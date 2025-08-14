import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from discord import File

from Defines import COMMAND_KEY, CONFIG, USER_DATA_FILE, GetUserData, SaveConfig, UserDataEntry
from SpotifyAccess import GetAllTracks, GetFullInfo
from Utility import SendMessage

COMMANDS: dict[str, Callable] = {}


async def OnTheList(message) -> None:
    for artistID in re.findall(CONFIG["Regex"]["artist"], message.content):
        defaulted: bool = False
        if artistID in CONFIG["Vibes"]:
            await SendMessage(
                f"{artistID} -> Already in the list rated at {CONFIG["Vibes"][artistID]}",
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
                f"{artistID} logged at {rating}{" (defaulted)" if defaulted else ''}",
                message,
            )
            await SaveConfig()


async def Refresh(message) -> None:
    await SendMessage("Resetting myself 🔫", message)
    sys.exit(0)


async def Update(message) -> None:
    os.chdir(Path(__file__).parent.parent)
    results = subprocess.check_output(["git", "pull", "origin", "main"])
    await SendMessage(f"Pulled from Git: {results.decode("utf-8")}", message)
    await Refresh(message)


async def ListCommands(message) -> None:
    commands = sorted([str(x) for x in COMMANDS])
    await SendMessage(f"Current Commands:\n\t-> {"\n\t-> ".join(commands)}", message)


async def UserData(message):
    await SendMessage("Here is the user data file", message, True)
    await message.reply(file=File(USER_DATA_FILE))


async def Blame(message):
    for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
        for entry in [
            x for x in await GetUserData() if x.EntryStatus.WasSuccessful and x.TrackId == trackID
        ]:
            await SendMessage(f"{entry}", message, reply=True)


async def UserStats(message):
    data: list[UserDataEntry] = await GetUserData()
    addedSongs: list[UserDataEntry] = [x for x in data if x.EntryStatus.WasSuccessful]
    if "duration" in message.content:
        timed: dict[UserDataEntry, int] = {}

        for song in addedSongs:
            info = await GetFullInfo(song.TrackId)
            timed[song] = info["track"]["duration_ms"]

        sortedTimes: list[tuple[UserDataEntry, int]] = sorted(
            list(timed.items()), key=lambda x: x[1]
        )

        shortest = "Shortest:\n\t- " + "\n\t- ".join(
            [f"{x[0].TrackName} -> {x[1] / 1000} seconds" for x in sortedTimes[:5]]
        )
        longest = "Longest:\n\t- " + "\n\t- ".join(
            [f"{x[0].TrackName} -> {x[1] / 1000} seconds" for x in reversed(sortedTimes[-5:])]
        )

        await SendMessage(shortest, message, reply=True)
        await SendMessage(longest, message, reply=True)

    if "posters" in message.content:
        addFreq = {
            uname: len([entry for entry in addedSongs if entry.User == uname])
            for uname in {x.User for x in data}
        }
        addFreq = sorted(list(addFreq.items()), key=lambda x: x[1], reverse=True)
        outStr = "Top Posters:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])
        await SendMessage(outStr, message, reply=True)
    if "artists" in message.content:
        addFreq = {
            artist: len([entry for entry in addedSongs if entry.Artist == artist])
            for artist in {x.Artist for x in data}
        }
        addFreq = sorted(list(addFreq.items()), key=lambda x: x[1], reverse=True)
        addFreq = [x for x in addFreq if x[1] > 1]
        outStr = "Top Artists:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])
        await SendMessage(outStr, message, reply=True)
    if "genres" in message.content:
        genres = []
        await SendMessage("Loading genres (this may take a minute)", message, reply=True)
        for track in addedSongs:
            genres += (await GetFullInfo(track.TrackId))["artist"]["genres"]
        genreFreq = {x: genres.count(x) for x in set(genres)}
        genreFreq = [
            x for x in sorted(list(genreFreq.items()), key=lambda x: x[1], reverse=True) if x[1] > 1
        ]
        outStr = "Top Genres:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in genreFreq])
        await SendMessage(outStr, message, reply=True)


async def CheckTracks(message):
    data = await GetUserData()
    playlistTracks = []
    found = 0
    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        playlistTracks = GetAllTracks(playlistID)
    for track in playlistTracks:
        if len([x for x in data if x.TrackId == track["track"]["id"]]) < 1:
            await SendMessage(
                f"Error, no matching data for {track["track"]["name"]} {track["track"]["artists"][0]["name"]} ({track["track"]["id"]})",
                message,
            )
            found += 1
    await SendMessage(f"{found} Errors Found", message)


async def Kill(message):
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


async def HandleCommands(message) -> bool:
    handled = False
    for key, command in COMMANDS.items():
        if re.match(COMMAND_KEY + key, message.content):
            await command(message)
            handled = True
    if not handled:
        await SendMessage(
            "I think that was supposed to be a command, but none I recognized", message, reply=True
        )
    return handled
