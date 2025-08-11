import asyncio
import datetime as dt
import math
import random
import re

from Commands import HandleCommands, SendMessage
from DataLogging import GetResponse, LogUserData
from Defines import CONFIG, DISCORD_CLIENT, MEMORY, SaveMemory, Status, TimeToSec
from SpotifyAccess import AddToPlaylist, ForceTrack


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
                await SendMessage("🎶 What is @everyone listening to? 🎶", c)
                MEMORY["Poked"] = True
                await SaveMemory()
            else:
                print("Can't find channel for poke")


@DISCORD_CLIENT.listen("on_ready")
async def ReAnnounce():
    if channel := DISCORD_CLIENT.get_channel(MEMORY["LastChannel"]):
        await SendMessage("I'm back 😎", channel)
    else:
        print("Can't find channel for announce")
    await Poke()


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


async def Main():
    asyncio.create_task(Poke())


if __name__ == "__main__":
    asyncio.run(Main())
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
