"""Commands for spotify bot."""

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from Defines import (
    COMMAND_KEY,
    CONFIG,
    USER_DATA_FILE,
    GetMemory,
    GetUserData,
    SaveConfig,
    UserDataEntry,
)
from discord import File, Message
from SpotifyAccess import GetAllTracks, GetFullInfo
from Utility import SendMessage

COMMANDS: dict[str, Callable] = {}
STATS = ["genres", "artists", "duration", "posters"]


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
            await SendMessage(
                f"{artistID} logged at {rating}{' (defaulted)' if defaulted else ''}",
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
    )
    await SendMessage(f"Current Commands:\n\t-> {'\n\t-> '.join(commands)}", message)


async def UserData(message: Message) -> None:
    """Send the user data file.

        Args:
            message (Message): triggering message
    _
    """
    await SendMessage("Here is the user data file", message, True)
    await message.reply(file=File(USER_DATA_FILE))


async def Blame(message: Message) -> None:
    """Determine who added a song.

    Args:
        message (Message): triggering message

    """
    for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
        for entry in [
            x
            for x in await GetUserData()
            if x.EntryStatus.WasSuccessful and x.TrackId == trackID
        ]:
            await SendMessage(f"{entry}", message, reply=True)


async def UserStats(message: Message) -> None:
    """Get statistics for track additions.

    Args:
        message (Message): triggering message
    """
    data: list[UserDataEntry] = await GetUserData()
    statCount: int = 5
    useReverse: bool = "reverse" not in message.content
    addedSongs: list[UserDataEntry] = [x for x in data if x.EntryStatus.WasSuccessful]
    if "duration" in message.content:
        timed: dict[UserDataEntry, int] = {}
        for song in addedSongs:
            info = await GetFullInfo(song.TrackId)
            timed[song] = info["track"]["duration_ms"]
        sortedTimes: list[tuple[UserDataEntry, int]] = sorted(
            timed.items(),
            key=lambda x: x[1],
        )

        shortest = "Shortest:\n- " + "\n- ".join(
            [f"{x[1] / 1000} seconds -> {x[0].TrackInfo}" for x in sortedTimes[:5]],
        )
        longest = "Longest:\n- " + "\n- ".join(
            [
                f"{x[1] / 1000} seconds -> {x[0].TrackInfo}"
                for x in reversed(sortedTimes[-5:])
            ],
        )

        await SendMessage(shortest, message, reply=True)
        await SendMessage(longest, message, reply=True)

    if "posters" in message.content:
        addFreq = {
            uname: len([entry for entry in addedSongs if entry.User == uname])
            for uname in {x.User for x in data}
        }
        addFreq = sorted(addFreq.items(), key=lambda x: x[1], reverse=True)
        outStr = "Top Posters:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])
        await SendMessage(outStr, message, reply=True)
    if "cool" in message.content:
        results = {}
        for uname in {x.User for x in data}:
            totalSongs = 0
            totalPopularity = 0
            for entry in addedSongs:
                if entry.User == uname and entry.EntryStatus.WasSuccessful:
                    t = await GetFullInfo(entry.TrackId)
                    totalPopularity += (
                        t["artist"]["popularity"]
                        if "followers" not in message.content
                        else t["artist"]["followers"]["total"]
                    )
                    totalSongs += 1
            if totalSongs != 0:
                results[uname] = round(totalPopularity / totalSongs, 2)
        cool = sorted(results.items(), key=lambda x: x[1], reverse=not useReverse)
        outStr = "Coolest Posters:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in cool])
        await SendMessage(outStr, message, reply=True)
    if "artists" in message.content:
        addFreq = {
            artist: len([entry for entry in addedSongs if entry.Artist == artist])
            for artist in {x.Artist for x in data}
        }
        addFreq = sorted(addFreq.items(), key=lambda x: x[1], reverse=useReverse)
        addFreq = (
            [x for x in addFreq if x[1] >= addFreq[statCount][1]]
            if useReverse
            else [x for x in addFreq if x[1] <= addFreq[statCount][1]]
        )
        if len(addFreq) > 2 * statCount:
            addFreq = addFreq[: 2 * statCount]
        outStr = "Top Artists:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])
        await SendMessage(outStr, message, reply=True)
    if "genres" in message.content:
        genres: list[str] = []
        for track in addedSongs:
            genres += (await GetFullInfo(track.TrackId))["artist"]["genres"]
        genreFreq = {x: genres.count(x) for x in set(genres)}
        genreFreq = [
            x
            for x in sorted(genreFreq.items(), key=lambda x: x[1], reverse=useReverse)
            if x[1] > 1
        ]
        genreFreq = (
            [x for x in genreFreq if x[1] >= genreFreq[statCount][1]]
            if useReverse
            else [x for x in genreFreq if x[1] <= genreFreq[statCount][1]]
        )
        if len(genreFreq) > 2 * statCount:
            addFreq = genreFreq[: 2 * statCount]
        outStr = "Top Genres:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in genreFreq])
        await SendMessage(outStr, message, reply=True)
    if "unlabeled" in message.content:
        mem = await GetMemory()
        artists = [x for x in mem["Cache"]["artists"].values() if x["genres"] == []]
        messageStr = "Missing Genres:\n" + "\n".join([x["name"] for x in artists])
        await SendMessage(messageStr, message, True)
    if "popularity" in message.content:
        popularity = {}
        for track in addedSongs:
            trackInfo = await GetFullInfo(track.TrackId)
            if trackInfo["artist"]["name"] not in popularity:
                popularity[trackInfo["artist"]["name"]] = (
                    trackInfo["artist"]["popularity"]
                    if "followers" not in message.content
                    else trackInfo["artist"]["followers"]["total"]
                )
        popularity = sorted(popularity.items(), key=lambda x: x[1], reverse=useReverse)
        popularity = (
            [x for x in popularity if x[1] >= popularity[statCount][1]]
            if useReverse
            else [x for x in popularity if x[1] <= popularity[statCount][1]]
        )
        if len(popularity) > 2 * statCount:
            popularity = popularity[: 2 * statCount]
        outStr = "Popularity Rankings:\n" + "\n".join(
            [f"{x[0]}: {x[1]}" for x in popularity]
        )
        await SendMessage(outStr, message, reply=True)


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
