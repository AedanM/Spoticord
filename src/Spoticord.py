import asyncio
import datetime as dt
import math
import random
import re

from Commands import HandleCommands, SendMessage
from DataLogging import GetResponse, LogUserData, SaveConfig
from Defines import CONFIG, DISCORD_CLIENT, Status
from discord.ext import tasks
from SpotifyAccess import AddToPlaylist, ForceTrack


@tasks.loop(seconds=60)
async def Poke() -> None:
    today: dt.datetime = dt.datetime.today()
    current = seconds = (today.hour * 60 + today.minute) * 60 + today.second
    if CONFIG["PokeTime"].date() != today.date():
        CONFIG["Poked"] = False
        seconds = 0
        while seconds < current:
            startSecs, endSecs = random.choice(CONFIG["PokeTimes"][dt.datetime.now().weekday()])
            seconds = random.randint(startSecs, endSecs)
            newTime = dt.time(
                hour=math.floor(seconds / 3600),
                minute=math.floor(seconds / 60) % 60,
                second=seconds % 60,
            )
            CONFIG["PokeTime"] = dt.datetime.combine(today.date(), newTime)
        await SaveConfig()
    elif CONFIG["Poked"] == False and CONFIG["PokeTime"].timestamp() < today.timestamp():
        for channel in CONFIG["PokeChannels"]:
            if c := DISCORD_CLIENT.get_channel(channel):
                await SendMessage("🎶 What is @everyone listening to? 🎶", c)
                CONFIG["Poked"] = True
                await SaveConfig()
            else:
                print("Can't find channel for poke")


@DISCORD_CLIENT.listen("on_ready")
async def ReAnnounce():
    if channel := DISCORD_CLIENT.get_channel(CONFIG["LastChannel"]):
        await SendMessage("I'm back 😎", channel)
    else:
        print("Can't find channel for announce")


@DISCORD_CLIENT.listen("on_message")
async def MessageHandler(message):
    username: str = str(message.author).split("#", maxsplit=1)[0]
    isTesting: bool = "test" in message.channel.name
    logged: bool = False

    if await HandleCommands(message, isTesting):
        return

    if playlistID := CONFIG["Channel Maps"].get(message.channel.name, None):
        for trackID in re.findall(
            r"https://open.spotify.com/track/([a-zA-Z0-9]+)", message.content
        ):
            status, trackInfo = (
                ForceTrack(trackID, playlistID)
                if "!force" in message.content[:7]
                else AddToPlaylist(trackID, playlistID, isTesting)
            )

            if response := GetResponse(status, username, isTesting):
                await SendMessage(response, message.channel)

            await LogUserData(trackInfo, username, status, isTesting)

            logged = True

        if not logged and "open.spotify" in message.content:
            if response := GetResponse(Status.RegexFail, username, isTesting):
                await SendMessage(response, message.channel)

            await LogUserData(
                (message.content, "", ""),
                username,
                Status.RegexFail,
                isTesting,
            )


if __name__ == "__main__":
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
