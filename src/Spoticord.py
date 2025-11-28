"""Main of Spoticord Bot."""

import datetime as dt
import math
import random
import re

from discord import Message
from discord.ext import tasks

from Commands import HandleCommands
from DataLogging import GetResponse, LogUserData
from Defines import COMMAND_KEY, CONFIG, DISCORD_CLIENT, GetMemory, SaveMemory, Status
from SpotifyAccess import AddToPlaylist, ForceTrack
from Utility import DadMode, NotifyPlaylistLength, NotifyUserLength, SendMessage, TimeToSec


@tasks.loop(seconds=300)
async def Poke() -> None:
    """Poke chat to see whats going on."""
    today: dt.datetime = dt.datetime.today()
    now = await TimeToSec(today.time())
    memory = await GetMemory()
    if memory["PokingTime"].date() != today.date():
        memory["Poked"] = False
        seconds = 0
        pokeTimes = CONFIG["PokeTimes"][dt.datetime.now().weekday()]
        random.shuffle(pokeTimes)
        for startSecs, endSecs in pokeTimes:
            seconds = random.randint(startSecs, endSecs)
            newTime = dt.time(
                hour=math.floor(seconds / 3600),
                minute=math.floor(seconds / 60) % 60,
                second=seconds % 60,
            )
            memory["PokingTime"] = dt.datetime.combine(today.date(), newTime)
            if seconds < now:
                break
        if seconds == 0:
            memory["Poked"] = True
        await SaveMemory()
    elif not memory["Poked"] and await TimeToSec(memory["PokingTime"].time()) < now:
        for channel in CONFIG["PokeChannels"]:
            if c := DISCORD_CLIENT.get_channel(int(channel)):
                await SendMessage("🎶 What is @everyone listening to? 🎶", c, useChannel=True)
                memory["Poked"] = True
                await SaveMemory()
            else:
                print("Can't find channel for poke")


@tasks.loop(seconds=600)
async def SpecialTimes() -> None:
    """Send messages at special times."""
    today = dt.datetime.now()
    memory = await GetMemory()
    for event in CONFIG["SpecialTimes"]:
        if today.weekday() != event["Day"]:
            continue
        if await TimeToSec(today.time()) < int(event["Time"]):
            continue
        if memory["SpecialTimes"][event["ID"]]:
            continue
        if channel := DISCORD_CLIENT.get_channel(int(event["Channel"])):
            await SendMessage(event["Message"], channel, useChannel=True)
            memory["SpecialTimes"][event["ID"]] = True
            # reset the other days
            for e in CONFIG["SpecialTimes"]:
                if today.weekday() != e["Day"]:
                    memory["SpecialTimes"][e["ID"]] = False
            await SaveMemory()
        else:
            print(f"Tried to send message on {channel} and failed")


@DISCORD_CLIENT.listen("on_ready")
async def ReAnnounce() -> None:
    """On first boot, say you're back."""
    if channel := DISCORD_CLIENT.get_channel(CONFIG["Announce"]):
        await SendMessage("I'm back 😎", channel, useChannel=True)
    else:
        print("Can't find channel for announce")
    Poke.start()  # pyright: ignore[reportFunctionMemberAccess]
    SpecialTimes.start()  # pyright: ignore[reportFunctionMemberAccess]


@DISCORD_CLIENT.listen("on_message")
async def MessageHandler(message: Message) -> None:
    """Handle all messages sent on server.

    Parameters
    ----------
    message : Message
        message sent in chat
    """
    username: str = str(message.author).split("#", maxsplit=1)[0]
    isTesting: bool = "test" in message.channel.name
    logged: bool = False

    if username != "Spoticord":
        await DadMode(message)
    else:
        return

    if message.content and message.content[0] == COMMAND_KEY and (await HandleCommands(message)):
        return

    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        for trackID in re.findall(CONFIG["Regex"]["track"], message.content):
            status, trackInfo = (
                await ForceTrack(trackID, playlistID)
                if "!force" in message.content[:7]
                else await AddToPlaylist(trackID, playlistID, isTesting)
            )
            if status == Status.Repeat:
                username = trackInfo[-1]
            if response := GetResponse(status, username, isTesting):
                await SendMessage(response, message, reply=True)

            await LogUserData(trackInfo, username, status, isTesting)
            if status.WasSuccessful:
                await NotifyPlaylistLength(message)
                await NotifyUserLength(message)
            logged = True

        if not logged and "open.spotify" in message.content:
            if response := GetResponse(Status.RegexFail, username, isTesting):
                await SendMessage(response, message, reply=True)

            await LogUserData(
                (message.content.replace("\n", "\\n"), "", "", ""),
                username,
                Status.RegexFail,
                isTesting,
            )


if __name__ == "__main__":
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
