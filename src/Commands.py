"""Commands for spotify bot."""

import copy
import os
import random
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd
from discord import File, Message
from more_itertools import chunked

from DataLogging import LogEntry
from Defines import (
    COMMAND_KEY,
    CONFIG,
    MASTER_GENRES,
    TEMP_USER_DATA_FILE,
    USER_DATA_FILE,
    GetMemory,
    GetUserData,
    SaveConfig,
    SaveMemory,
    Status,
    UserDataEntry,
)
from Graphing import GRAPHS, Graphs, PrepDataFrame, PrepUserData
from SpotifyAccess import GetAllTracks, GetArtistInfo
from Stats import FilterData, UserStats
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
    await message.reply("Generating graphs, this may take a moment...")
    created = await Graphs(message)
    files = [File(x) for x in created]
    if files:
        for c in chunked(files, 10):
            await message.reply(files=c)
    else:
        await message.reply("No graphs were created, did you specify a valid type?")


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
    commands = list(COMMANDS.keys())
    commands.remove("stats")
    commands.remove("graph")
    out = f"Current Commands:\n\t-> {'\n\t-> '.join(commands)}"
    out += "\n\nStats Commands:\n\t-> " + "\n\t-> ".join(STATS)
    out += "\n\nGraph Commands:\n\t-> " + "\n\t-> ".join(GRAPHS)
    await SendMessage(out, message)


async def Data(message: Message) -> None:
    """Send the user data file.

        Args:
            message (Message): triggering message
    _
    """
    if "personal" in message.content:
        df = await PrepDataFrame()
        valid = df.loc[df["result"] == Status.Added]
        if isinstance(valid, pd.Series):
            await SendMessage("Not enough data to generate report", message, reply=True)
            return
        report: str = "Play%\tGenre\tArtist\tPop\tScore\tUser\n"
        userData = await PrepUserData(valid)
        for uname in userData["names"]:
            ud = userData[userData["names"] == uname].iloc[0]
            report += (
                f"{ud['playlist_%']:02.2f}\t"
                f"{ud['genre_ratio']:02.2f}\t"
                f"{ud['artist_ratio']:02.2f}\t"
                f"{ud['median_popularity']:02.2f}\t"
                f"{f'{ud["overall_score"]:02.2f}'}\t"
                f"{uname:20}\n"
            )
        await SendMessage(
            report,
            message,
            reply=True,
        )
    elif "popularity" not in message.content and "users" not in message.content:
        await SendMessage("Generating the user data file", message, True)
        await message.reply(file=File(USER_DATA_FILE))
    elif "users" in message.content:
        await SendMessage("Generating the user data file", message, True)
        df = await PrepDataFrame()
        valid = df.loc[df["result"] == Status.Added]
        if isinstance(valid, pd.Series):
            await SendMessage("Not enough data to generate report", message, reply=True)
            return
        await PrepUserData(valid, True)
        await message.reply(file=File(TEMP_USER_DATA_FILE))
    else:
        await SendMessage("Generating the user data file", message, True)
        await PrepDataFrame(True)
        await message.reply(file=File(TEMP_USER_DATA_FILE))


async def Blame(message: Message) -> None:
    """Determine who added a song.

    Args:
        message (Message): triggering message

    """
    author = str(message.author).split("#", maxsplit=1)[0]
    for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
        for entry in [
            x for x in await GetUserData() if x.EntryStatus.WasSuccessful and x.TrackId == trackID
        ]:
            newEntry = copy.deepcopy(entry)
            newEntry.Bonus = f"Blame from {author}"
            newEntry.EntryStatus = Status.Blamed
            if author == entry.User:
                await SendMessage(
                    "You added this one, double blame for you!!",
                    message,
                    reply=True,
                )
                await LogEntry(newEntry, False)
                await LogEntry(newEntry, False)
            else:
                await SendMessage(
                    f"You can blame {entry.User} for {entry.TrackInfo}",
                    message,
                    reply=True,
                )
                await LogEntry(newEntry, False)


async def Praise(message: Message) -> None:
    """Determine who added a song.

    Args:
        message (Message): triggering message

    """
    author = str(message.author).split("#", maxsplit=1)[0]
    for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
        for entry in [
            x for x in await GetUserData() if x.EntryStatus.WasSuccessful and x.TrackId == trackID
        ]:
            if author == entry.User:
                await SendMessage(
                    "You added this one, no praise for you!",
                    message,
                    reply=True,
                )
            else:
                await SendMessage(
                    f"Big Ups to {entry.User} for {entry.TrackInfo}",
                    message,
                    reply=True,
                )
                newEntry = copy.deepcopy(entry)
                newEntry.Bonus = f"Praise from {author}"
                newEntry.EntryStatus = Status.Praised
                await LogEntry(newEntry, False)


async def Validate(message: Message) -> None:
    """Check to ensure all tracks are accounted for in data log.

    Args:
        message (Message): triggering message

    """
    missing: list[tuple[str, str, str]] = []
    for idStr, m in (await GetMemory())["Cache"]["artists"].items():
        if isinstance(m, list):
            print(m, idStr)
        else:
            if not any(x in "".join(m["genres"]) for x in MASTER_GENRES):
                missing.append((m["name"], idStr, m["genres"]))
    await SendMessage(
        f"{len(missing)} Artists Missing Genres:\n - "
        + "\n - ".join(f"{x[0]} ({x[1]}) {x[2]}" for x in missing),
        message,
    )

    data = await GetUserData()
    playlistTracks = []
    found = 0
    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        playlistTracks = GetAllTracks(playlistID)
    for track in playlistTracks:
        if len([x for x in data if x.TrackId == track["track"]["id"]]) < 1:
            await SendMessage(
                (
                    "Error, no matching data for "
                    f"({track['added_at']}),"
                    f"({track['track']['id']}),"
                    f"{track['track']['name']}, "
                    f"{track['track']['artists'][0]['name']}, "
                    f"{track['track']['uri']}, "
                ),
                message,
            )
            found += 1
    await SendMessage(f"{found} Unaccounted Entries Found", message)


async def Kill(message: Message) -> None:
    """Kill Current Process.

    Args:
        message (Message): triggering message

    """
    await SendMessage("", message)
    sys.exit(0)


async def CheckArtist(message: Message) -> None:
    """Get info on an artist from their ID.

    Args:
        message (Message): triggering message

    """
    for artistID in re.findall(CONFIG["Regex"]["artist"], message.content):
        artist = (await GetArtistInfo(artistID))["artist"]
        await SendMessage(
            f"{artist['name']}:\n"
            f"Followers: {artist['followers']['total']}\n"
            f"Popularity: {artist['popularity']}\n"
            f"Genres: {artist['genres']}",
            message,
        )


async def AddGenre(message: Message) -> None:
    """Add genre(s) to an artist from their ID."""
    mem = message.content
    save = " save" in message.content
    if save:
        mem = mem.replace(" save", "")
    if match := re.match(r"!addGenre\s([\w]{22})\s(.*)", mem):
        artistID, genres = match.groups()
        info = (await GetArtistInfo(artistID))["artist"]
        info["genres"] = sorted(
            set(
                (info["genres"] if isinstance(info["genres"], list) else [])
                + [x.strip() for x in genres.split(",")],
            ),
        )

        await SendMessage(f"Genres for {info['name']} now {info['genres']}", message)
        if save:
            await SaveMemory()
    else:
        await SendMessage("Failed regex", message, reply=True)


async def Playlist(message: Message) -> None:
    """Generate a random sample of the playlist."""
    data: list[UserDataEntry] = await GetUserData()
    valid = [x for x in data if x.EntryStatus == Status.Added]
    async def Formatter(x,_y):
        return x.TrackInfo
    inputData: dict = {
        "Data": dict([(entry, random.random()) for entry in valid]), 
        "Title": "Random Sample from Playlist",
        "Formatter": Formatter,
    }
    results = await FilterData(message, inputData)
    outStr = str(inputData["Title"]) + ":\n"
    outStr += "\n".join(
        [f" - {await inputData['Formatter'](entry, rng)}" for entry, rng in results["Filtered"]],
    )
    await SendMessage(outStr, message)


COMMANDS = {
    "blame": Blame,
    "praise": Praise,
    "checkArtist": CheckArtist,
    "addGenre": AddGenre,
    "validate": Validate,
    "commands": ListCommands,
    "data": Data,
    "graph": Graph,
    "kill": Kill,
    "onTheList": OnTheList,
    "refresh": Refresh,
    "stats": UserStats,
    "update": Update,
    "playlist": Playlist,
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
            break
    if not handled and "!force" not in message.content:
        await SendMessage(
            output="I think that was supposed to be a command, but none I recognized",
            contextObj=message,
            reply=True,
        )
    return handled
