"""Commands for spotify bot."""

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd
from discord import File, Message

from Defines import (
    COMMAND_KEY,
    CONFIG,
    TEMP_USER_DATA_FILE,
    USER_DATA_FILE,
    GetUserData,
    SaveConfig,
)
from Graphing import GRAPHS, Graphs, PrepDataFrame
from SpotifyAccess import GetAllTracks, GetArtistInfo
from Stats import UserStats
from Utility import SendMessage

COMMANDS: dict[str, Callable] = {}
STATS = [
    "artists",
    "duration",
    "genres",
    "mainstream",
    "mainstream personal",
    "popularity",
    "posters",
    "graph",
]


async def Graph(message: Message) -> None:
    """Render stats graphs.

    Args:
        message (Message): triggering message
    """
    created = Graphs(message)
    files = [File(x) for x in created]
    if files:
        await message.reply(files=files)


async def OnTheList(message: Message) -> None:
    """Add an artist to the ban list.

    Args:
        message (Message): triggering message
    """
    for artistID in re.findall(CONFIG["Regex"]["artist"], message.content):
        defaulted: bool = False
        if artistID in CONFIG["Vibes"]:
            await SendMessage(
                f"{artistID} -> Already in the list rated at {CONFIG['Vibes'][artistID]}",
                message,
            )
        else:
            try:
                if ratingStr := re.search(
                    r"\s[0-9\.]+",
                    str(message.content)[str(message.content).index(artistID) :],
                ):
                    rating = float(ratingStr.group())
                else:
                    raise ValueError
            except ValueError:
                defaulted = True
                rating = 1.0
            CONFIG["Vibes"][artistID] = rating
            info = (await GetArtistInfo(artistID))["artist"]
            await SendMessage(
                f"{info['name']} logged at {rating}{' (defaulted)' if defaulted else ''}",
                message,
            )
            await SaveConfig()


async def Refresh(message: Message) -> None:
    """End and restart process.

    Args:
        message (Message): triggering message

    """
    await SendMessage("Resetting myself 🔫", message)
    sys.exit(0)


async def Update(message: Message) -> None:
    """Pull from github and restart process.

    Args:
        message (Message): triggering message

    """
    os.chdir(Path(__file__).parent.parent)
    results = subprocess.check_output(["git", "pull", "origin", "main"])  # noqa: S607
    await SendMessage(f"Pulled from Git: {results.decode('utf-8')}", message)
    await Refresh(message)


async def ListCommands(message: Message) -> None:
    """List all available commands.

    Args:
        message (Message): triggering message

    """
    commands = sorted(
        [str(x) for x in list(COMMANDS.keys()) + [f"stats {y}" for y in STATS]]
        + [f"graph {y}" for y in GRAPHS],
    )
    await SendMessage(f"Current Commands:\n\t-> {'\n\t-> '.join(commands)}", message)


async def UserData(message: Message) -> None:
    """Send the user data file.

        Args:
            message (Message): triggering message
    _
    """
    await SendMessage("Here is the user data file", message, True)
    if "popularity" not in message:
        await message.reply(file=File(USER_DATA_FILE))
    else:
        PrepDataFrame()
        await message.reply(file=File(TEMP_USER_DATA_FILE))


async def Blame(message: Message) -> None:
    """Determine who added a song.

    Args:
        message (Message): triggering message

    """
    for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
        for entry in [
            x for x in await GetUserData() if x.EntryStatus.WasSuccessful and x.TrackId == trackID
        ]:
            await SendMessage(f"{entry}", message, reply=True)


async def CheckTracks(message: Message) -> None:
    """Check to ensure all tracks are accounted for in data log.

    Args:
        message (Message): triggering message

    """
    data = await GetUserData()
    playlistTracks = []
    found = 0
    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        playlistTracks = GetAllTracks(playlistID)
    for track in playlistTracks:
        if len([x for x in data if x.TrackId == track["track"]["id"]]) < 1:
            await SendMessage(
                (
                    f"Error, no matching data for {track['track']['name']} "
                    f"{track['track']['artists'][0]['name']} "
                    f"({track['track']['id']})"
                ),
                message,
            )
            found += 1
    await SendMessage(f"{found} Errors Found", message)


async def Kill(message: Message) -> None:
    """Kill Current Process.

    Args:
        message (Message): triggering message

    """
    await SendMessage("", message)
    sys.exit(0)


async def CacheArtist(message: Message) -> None:
    """Get info on an artist from their ID.

    Args:
        message (Message): triggering message

    """
    for artistID in re.findall(CONFIG["Regex"]["artist"], message.content):
        artist = (await GetArtistInfo(artistID))["artist"]
        await SendMessage(
            f"{artist['name']} - "
            f"Followers: {artist['followers']['total']} - "
            f"Popularity: {artist['popularity']}",
            message,
        )


COMMANDS = {
    "blame": Blame,
    "check": CheckTracks,
    "commands": ListCommands,
    "kill": Kill,
    "onTheList": OnTheList,
    "refresh": Refresh,
    "stats": UserStats,
    "update": Update,
    "userData": UserData,
    "cacheArtist": CacheArtist,
    "graph": Graph,
    "force": lambda _x: ...,
}


async def HandleCommands(message: Message) -> bool:
    """Switchboard for user commands.

    Args:
        message (Message): triggering message

    Returns
    -------
        bool: true if command used

    """
    handled = False
    for key, command in COMMANDS.items():
        if re.match(COMMAND_KEY + key, message.content):
            await command(message)
            handled = True
    if not handled:
        await SendMessage(
            output="I think that was supposed to be a command, but none I recognized",
            contextObj=message,
            reply=True,
        )
    return handled
