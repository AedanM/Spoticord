import asyncio
import re
import sys
from typing import Callable

from Defines import CONFIG, CONFIG_PATH
from yaml import Dumper, dump

CONFIG_LOCK = asyncio.Lock()
COMMANDS: dict[str, Callable] = {}


async def OnTheList(message, isTesting):
    for artistID in re.findall(r"https://open.spotify.com/artist/([a-zA-Z0-9]+)", message.content):
        if artistID in CONFIG["Vibes"]:
            await message.channel.send(
                f"{artistID} -> Already in the list rated at {CONFIG["Vibes"][artistID]}"
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
                await message.channel.send(
                    f"Could not determine new rating for {artistID}, defaulting to 1.0"
                )
                rating = 1.0
            CONFIG["Vibes"][artistID] = rating
            await message.channel.send(f"{artistID} logged at {rating}")
            async with CONFIG_LOCK:
                dump(CONFIG, CONFIG_PATH.open(mode="w", encoding="utf-8"), Dumper=Dumper)


async def Refresh(message, isTesting):
    await message.channel.send("Resetting myself 🔫")
    sys.exit()


async def ListCommands(message, isTesting):
    commands = sorted([str(x) for x in COMMANDS.keys()])
    await message.channel.send(f"Current Commands:\n\t-> {"\n\t-> ".join(commands)}")


COMMANDS = {"!onTheList": OnTheList, "!refresh": Refresh, "!commands": ListCommands}


async def HandleCommands(message, isTesting) -> bool:
    handled = False
    for command in COMMANDS:
        if re.match(command, message.content):
            await COMMANDS[command](message, isTesting)
            handled = True
    return handled
