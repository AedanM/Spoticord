"""Defines for Spoticord bot."""

import asyncio
import csv
import datetime
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import discord
import spotipy
from discord.ext import commands
from spotipy.oauth2 import SpotifyOAuth
from yaml import Dumper, dump
from yaml import safe_load as load

Dumper.ignore_aliases = lambda *_args: True  # pyright: ignore[reportAttributeAccessIssue]


class Status(StrEnum):
    """Status enumeration for attempts to add to playlist."""

    Default = ""
    Added = "Added"
    Failed = "Failed"
    Repeat = "Repeat"
    BadVibes = "Failed Vibes"
    RegexFail = "Failed Regex"
    WrongMarket = "Wrong Market"
    ForceAdd = "Forcefully Added"

    @property
    def WasSuccessful(self) -> bool:
        """Did the song go into the playlist."""
        return self in [Status.Added, Status.ForceAdd]


@dataclass
class UserDataEntry:
    """Representation of 1 line of user data log."""

    Artist: str
    EntryStatus: Status
    TimeAdded: datetime.datetime
    TrackId: str
    TrackName: str
    URI: str
    User: str

    @classmethod
    def FromList(cls, dataFields: list[str]) -> "UserDataEntry":
        """Create an instance from a list of dataFields.

        Parameters
        ----------
        dataFields : list[str]
            list of dataFields

        Returns
        -------
        UserDataEntry
            instance of class
        """
        return cls(
            Artist=dataFields[5],
            EntryStatus=Status(dataFields[2]),
            TimeAdded=datetime.datetime.fromisoformat(dataFields[0]),
            TrackId=dataFields[3],
            TrackName=dataFields[4],
            URI=dataFields[6],
            User=dataFields[1],
        )

    @classmethod
    def FromString(cls, s: str) -> "UserDataEntry":
        """Generate instance from string of values.

        Parameters
        ----------
        s : str
            string representation

        Returns
        -------
        UserDataEntry
            instance of user data entry
        """
        dataFields = list(csv.reader([s], delimiter=SEPARATOR, quotechar='"'))[0]
        return cls.FromList(dataFields)

    @property
    def OutputString(self) -> str:
        """Output to be logged in datafile.csv.

        Returns
        -------
        str
            csv string
        """
        return ",".join(
            [
                str(self.TimeAdded),
                self.User,
                str(self.EntryStatus),
                f'"{self.TrackId}"',
                f'"{self.TrackName}"',
                f'"{self.Artist}"',
                f'"{self.URI}"',
            ],
        )

    @property
    def TrackInfo(self) -> str:
        """Track name and artist, human readable.

        Returns
        -------
        str
            _description_
        """
        return f"{self.TrackName} - {self.Artist}"

    def __str__(self) -> str:
        """Return string repr of instance."""
        return f"{self.TrackInfo} {self.EntryStatus} by {self.User}"

    def __hash__(self) -> int:
        """Hash the data entry.

        Returns
        -------
        int
            hashed value
        """
        return hash(self.OutputString)


CACHE_FILE: Path = Path("data/cache.yml")
CONFIG_FILE: Path = Path("data/conf.yml" if len(sys.argv) < 2 else sys.argv[1])
MEMORY_FILE: Path = Path("data/memory.yml" if len(sys.argv) < 3 else sys.argv[2])
USER_DATA_FILE: Path = Path("data/user_data.csv")

CACHE_LOCK: asyncio.Lock = asyncio.Lock()
CONFIG_LOCK: asyncio.Lock = asyncio.Lock()
MEMORY_LOCK: asyncio.Lock = asyncio.Lock()
USER_DATA_FILE_LOCK: asyncio.Lock = asyncio.Lock()

UNAME_STAND_IN: str = "UNAME_STAND_IN"
COMMAND_KEY: str = "!"
SEPARATOR: str = ","

CONFIG: dict = load(CONFIG_FILE.read_text(encoding="utf-8"))
MEMORY: dict = {}
USER_DATA: list[UserDataEntry] = []

DISCORD_INTENTS: discord.Intents = discord.Intents.default()
DISCORD_INTENTS.message_content = True
DISCORD_CLIENT: discord.Client = commands.Bot(command_prefix="!*", intents=DISCORD_INTENTS)

SPOTIFY_SCOPE: str = "playlist-modify-public"
SPOTIFY_CLIENT: spotipy.Spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope=SPOTIFY_SCOPE,
        client_id=CONFIG["SpotifyID"],
        client_secret=CONFIG["SpotifySecret"],
        redirect_uri="http://127.0.0.1:3000",
    ),
)


async def SaveConfig() -> None:
    """Save config to disk."""
    async with CONFIG_LOCK:
        with CONFIG_FILE.open(encoding="utf-8", mode="w") as fp:
            dump(CONFIG, fp, Dumper=Dumper)


async def SaveMemory() -> None:
    """Save Memory to disk."""
    async with CACHE_LOCK:
        with CACHE_FILE.open(encoding="utf-8", mode="w") as fp:
            dump(MEMORY["Cache"], fp, Dumper=Dumper)
    async with MEMORY_LOCK:
        with MEMORY_FILE.open(encoding="utf-8", mode="w") as fp:
            dump(
                {key: value for key, value in MEMORY.items() if key != "Cache"},
                fp,
                Dumper=Dumper,
            )


async def GetUserData() -> list[UserDataEntry]:
    """Access user data, loads if not loaded yet."""
    if USER_DATA == []:
        await LoadUserData()
    return USER_DATA


async def GetMemory() -> dict:
    """Access memory, loads if not loaded yet."""
    if MEMORY == {}:
        await LoadMemory()
    return MEMORY


async def LoadUserData() -> None:
    """Load User data from disk."""
    global USER_DATA
    async with USER_DATA_FILE_LOCK:
        with USER_DATA_FILE.open(encoding="utf-8") as csvFile:
            USER_DATA = [
                UserDataEntry.FromList(x)
                for idx, x in enumerate(csv.reader(csvFile, delimiter=SEPARATOR, quotechar='"'))
                if idx != 0 and x != []
            ]


async def LoadMemory() -> None:
    """Load memory from disk."""
    global MEMORY
    async with MEMORY_LOCK:
        with MEMORY_FILE.open(encoding="utf-8", mode="r") as fp:
            MEMORY = load(fp)
        with CACHE_FILE.open(encoding="utf-8", mode="r") as fp:
            MEMORY["Cache"] = load(fp)


def AppendUserData(data: str) -> None:
    """Write to last line of user data log.

    Parameters
    ----------
    data : str
        input data from logging
    """
    # todo : change types
    userEntry = UserDataEntry.FromString(data)
    with USER_DATA_FILE.open(mode="a", encoding="utf-8") as fp:
        fp.write("\n" + userEntry.OutputString)
