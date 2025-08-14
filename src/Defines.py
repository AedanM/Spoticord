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
from yaml import Dumper, Loader, dump, load

Dumper.ignore_aliases = lambda *args: True  # type: ignore


class Status(StrEnum):
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
        return self in [Status.Added, Status.ForceAdd]


@dataclass
class UserDataEntry:
    Artist: str
    EntryStatus: Status
    TimeAdded: datetime.datetime
    TrackId: str
    TrackName: str
    URI: str
    User: str

    @classmethod
    def FromList(cls, dataFields) -> "UserDataEntry":
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
    def FromString(cls, s) -> "UserDataEntry":
        dataFields = [x.replace('"', "").strip() for x in s.split(",")]
        return cls.FromList(dataFields)

    @property
    def OutputString(self):
        return ",".join(
            [
                str(self.TimeAdded),
                self.User,
                str(self.EntryStatus),
                f'"{self.TrackId}"',
                f'"{self.TrackName}"',
                f'"{self.Artist}"',
                f'"{self.URI}"',
            ]
        )

    @property
    def TrackInfo(self) -> str:
        return f"{self.TrackName} - {self.Artist}"

    def __str__(self) -> str:
        return f"{self.TrackInfo} {self.EntryStatus} by {self.User}"

    def __hash__(self):
        return hash((str(self), str(self.TimeAdded), self.EntryStatus))


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

CONFIG: dict = load(CONFIG_FILE.read_text(encoding="utf-8"), Loader)
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
    )
)


async def SaveConfig() -> None:
    async with CONFIG_LOCK:
        with CONFIG_FILE.open(encoding="utf-8", mode="w") as fp:
            dump(CONFIG, fp, Dumper=Dumper)


async def SaveMemory() -> None:
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
    if USER_DATA == []:
        await LoadUserData()
    return USER_DATA


async def GetMemory() -> dict:
    if MEMORY == {}:
        await LoadMemory()
    return MEMORY


async def LoadUserData() -> None:
    global USER_DATA
    async with USER_DATA_FILE_LOCK:
        with USER_DATA_FILE.open(encoding="utf-8") as csvFile:
            USER_DATA = [
                UserDataEntry.FromList(x)
                for idx, x in enumerate(csv.reader(csvFile, delimiter=",", quotechar='"'))
                if idx != 0 and x != []
            ]


async def LoadMemory() -> None:
    global MEMORY
    async with MEMORY_LOCK:
        with MEMORY_FILE.open(encoding="utf-8", mode="r") as fp:
            MEMORY = load(fp, Loader)
        with CACHE_FILE.open(encoding="utf-8", mode="r") as fp:
            MEMORY["Cache"] = load(fp, Loader)


def AppendUserData(data: str):
    userEntry = UserDataEntry.FromString(data)
    with USER_DATA_FILE.open(mode="a", encoding="utf-8") as fp:
        fp.write("\n" + userEntry.OutputString)
