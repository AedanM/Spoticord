import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from Defines import COMMAND_KEY, CONFIG, MEMORY, USER_DATA_FILE, SaveConfig, SaveMemory
from discord import File

COMMANDS: dict[str, Callable] = {}


async def SendMessage(response, message, reply: bool = False, useChannel: bool = False):
    if useChannel:
        await message.send(response)
        id = message.id
    else:
        await (message.reply(response) if reply else message.channel.send(response))
        id = message.channel.id

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


COMMANDS = {
    "onTheList": OnTheList,
    "refresh": Refresh,
    "commands": ListCommands,
    "update": Update,
    "previewPoke": PreviewPoke,
    "userData": UserData,
    "blame": Blame,
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
