import os
import re
import subprocess
import sys
from pathlib import Path
from pprint import pp
from typing import Callable

from Defines import (
    COMMAND_KEY,
    CONFIG,
    MEMORY,
    USER_DATA_FILE,
    GetUserData,
    SaveConfig,
    SaveMemory,
    UserDataEntry,
)
from discord import File
from SpotifyAccess import GetAllTracks, GetFullInfo

COMMANDS: dict[str, Callable] = {}


async def NotifyPlaylistLength(response):
    playlistLen = len([x for x in await GetUserData() if x.EntryStatus.WasSuccessful])
    if playlistLen % CONFIG["UpdateInterval"] == 0:
        await SendMessage(f"This was song #{playlistLen} 🙌", response, reply=True)

    return


async def SendMessage(output, contextObj, reply: bool = False, useChannel: bool = False):
    if useChannel:
        await contextObj.send(output)
        id = contextObj.id
    else:
        await (contextObj.reply(output) if reply else contextObj.channel.send(output))
        id = contextObj.channel.id

    if MEMORY["LastChannel"] != id:
        MEMORY["LastChannel"] = str(id)
        await SaveMemory()


async def OnTheList(message) -> None:
    for artistID in re.findall(r"https://open.spotify.com/artist/([a-zA-Z0-9]+)", message.content):
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
    os.chdir(Path(__file__).parent)
    results = subprocess.check_output(["git", "pull", "origin", "main"])
    await SendMessage(f"Pulled from Git: {results}", message)
    await Refresh(message)


async def ListCommands(message) -> None:
    commands = sorted([str(x) for x in COMMANDS])
    await SendMessage(f"Current Commands:\n\t-> {"\n\t-> ".join(commands)}", message)


async def PreviewPoke(message):
    await SendMessage(f"Poke should occur around {MEMORY["PokeTime"]}", message)


async def UserData(message):
    await SendMessage("Here is the user data file", message, True)
    await message.reply(file=File(USER_DATA_FILE))


async def Blame(message):
    return
    # CURRENT_USER_DATA.rows_by_key(key="track", named=True)[]


async def UserStats(message):
    data: list[UserDataEntry] = await GetUserData()
    addedSongs = [x for x in data if x.EntryStatus.WasSuccessful]

    if "posters" in message.content:
        addFreq = {
            uname: len([entry for entry in addedSongs if entry.User == uname])
            for uname in set([x.User for x in data])
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
            genres += GetFullInfo(track.TrackId)["artist"]["genres"]
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


COMMANDS = {
    "onTheList": OnTheList,
    "refresh": Refresh,
    "commands": ListCommands,
    "update": Update,
    "previewPoke": PreviewPoke,
    "userData": UserData,
    "blame": Blame,
    "stats": UserStats,
    "check": CheckTracks,
}


async def HandleCommands(message) -> bool:
    handled = False
    for key, command in COMMANDS.items():
        if re.match(COMMAND_KEY + key, message.content):
            await command(message)
            handled = True
    if not handled:
        await SendMessage(
            f"I think that was supposed to be a command, but none I recognized",
            message,
        )
    return handled


async def DadMode(message):
    if subject := re.search(r"i'?\s?a?m\s\s?a?([^\.\?\!]+)", message.content.lower()):
        subject = subject.group(1)
        await SendMessage(f"Hi {subject}, I'm Spoticord", message, reply=True)
    if subject := re.search(r"make\sme\s?a?\s([^\.\?\!]+)", message.content.lower()):
        subject = subject.group(1)
        await SendMessage(f"Poof! You're a {subject}", message, reply=True)
