import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from DataLogging import SaveConfig
from Defines import CONFIG

COMMANDS: dict[str, Callable] = {}


async def SendMessage(message, channel):
    await channel.send(message)
    if CONFIG["LastChannel"] != channel.id:
        CONFIG["LastChannel"] = channel.id
        await SaveConfig()


async def OnTheList(message, isTesting: bool) -> None:
    for artistID in re.findall(r"https://open.spotify.com/artist/([a-zA-Z0-9]+)", message.content):
        defaulted: bool = False
        if artistID in CONFIG["Vibes"]:
            await SendMessage(
                f"{artistID} -> Already in the list rated at {CONFIG["Vibes"][artistID]}",
                message.channel,
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
                message.channel,
            )
            if not isTesting:
                await SaveConfig()


async def Refresh(message, _isTesting: bool) -> None:
    await SendMessage("Resetting myself 🔫", message.channel)
    sys.exit(0)


async def Update(message, isTesting: bool) -> None:
    os.chdir(Path(__file__).parent)
    results = subprocess.check_output(["git", "pull", "origin", "main"])
    await SendMessage(f"Pulled from Git: {results}", message.channel)
    await Refresh(message, isTesting)


async def ListCommands(message, _isTesting: bool) -> None:
    commands = sorted([str(x) for x in COMMANDS])
    await SendMessage(f"Current Commands:\n\t-> {"\n\t-> ".join(commands)}", message.channel)


async def PreviewPoke(message, _isTesting: bool):
    await SendMessage(f"Poke should occur around {CONFIG["PokeTime"]}", message.channel)


COMMANDS = {
    "!onTheList": OnTheList,
    "!refresh": Refresh,
    "!commands": ListCommands,
    "!update": Update,
    "!previewPoke": PreviewPoke,
}


async def HandleCommands(message, isTesting: bool) -> bool:
    handled = False
    for key, command in COMMANDS.items():
        if re.match(key, message.content):
            await command(message, isTesting)
            handled = True
    return handled
