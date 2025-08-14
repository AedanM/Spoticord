import asyncio
import datetime as dt
import math
import random
import re

from Commands import HandleCommands, NotifyPlaylistLength, SendMessage,DadMode
from DataLogging import GetResponse, LogUserData
from Defines import COMMAND_KEY, CONFIG, DISCORD_CLIENT, MEMORY, SaveMemory, Status, TimeToSec
from discord.ext import tasks
from SpotifyAccess import AddToPlaylist, ForceTrack


@tasks.loop(seconds=60)
async def Poke() -> None:
    today: dt.datetime = dt.datetime.today()
    now = await TimeToSec(today.time())
    if MEMORY["PokeTime"].date() != today.date():
        MEMORY["Poked"] = False
        seconds = 0
        while seconds < now:
            startSecs, endSecs = random.choice(CONFIG["PokeTimes"][dt.datetime.now().weekday()])
            seconds = random.randint(startSecs, endSecs)
            newTime = dt.time(
                hour=math.floor(seconds / 3600),
                minute=math.floor(seconds / 60) % 60,
                second=seconds % 60,
            )
            MEMORY["PokeTime"] = dt.datetime.combine(today.date(), newTime)
        await SaveMemory()
    elif MEMORY["Poked"] == False and await TimeToSec(MEMORY["PokeTime"].time()) < now:
        for channel in CONFIG["PokeChannels"]:
            if c := DISCORD_CLIENT.get_channel(int(channel)):
                await SendMessage("🎶 What is @everyone listening to? 🎶", c, useChannel=True)
                MEMORY["Poked"] = True
                await SaveMemory()
            else:
                print("Can't find channel for poke")


@tasks.loop(seconds=600)
async def SpecialTimes() -> None:
    today = dt.datetime.now()
    for event in CONFIG["SpecialTimes"]:
        if today.weekday() != event["Day"]:
            continue
        if await TimeToSec(today.time()) < int(event["Time"]):
            continue
        if MEMORY["SpecialTimes"][event["ID"]]:
            continue
        if channel := DISCORD_CLIENT.get_channel(int(event["Channel"])):
            await SendMessage(event["Message"], channel, useChannel=True)
            MEMORY["SpecialTimes"][event["ID"]] = True
            # reset the other days
            for e in CONFIG["SpecialTimes"]:
                if today.weekday() != e["Day"]:
                    MEMORY["SpecialTimes"][e["ID"]] = False
            await SaveMemory()
        else:
            print(f"Tried to send message on {channel} and failed")


@DISCORD_CLIENT.listen("on_ready")
async def ReAnnounce():
    if channel := DISCORD_CLIENT.get_channel(int(MEMORY["LastChannel"])):
        await SendMessage("I'm back 😎", channel, useChannel=True)
    else:
        print("Can't find channel for announce")
    Poke.start()  # type:ignore
    SpecialTimes.start()  # type:ignore


@DISCORD_CLIENT.listen("on_message")
async def MessageHandler(message):
    username: str = str(message.author).split("#", maxsplit=1)[0]
    isTesting: bool = "test" in message.channel.name
    logged: bool = False

    if username != "Spoticord":
        await DadMode(message)
    
    if message.content and message.content[0] == COMMAND_KEY and await HandleCommands(message):
        return

    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        for trackID in re.findall(
            r"https://open.spotify.com/track/([a-zA-Z0-9]+)", message.content
        ):
            status, trackInfo = (
                ForceTrack(trackID, playlistID)
                if "!force" in message.content[:7]
                else await AddToPlaylist(trackID, playlistID, isTesting)
            )
            if status.WasSuccessful:
                await NotifyPlaylistLength(message)
            if response := GetResponse(status, username, isTesting):
                await SendMessage(response, message, reply=True)

            await LogUserData(trackInfo, username, status, isTesting)

            logged = True

        if not logged and "open.spotify" in message.content:
            if response := GetResponse(Status.RegexFail, username, isTesting):
                await SendMessage(response, message, reply=True)

            await LogUserData(
                (message.content, "", "", ""),
                username,
                Status.RegexFail,
                isTesting,
            )


if __name__ == "__main__":
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
