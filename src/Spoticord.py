import re

from Commands import HandleCommands
from DataLogging import LogUserData
from Defines import CONFIG, DISCORD_CLIENT, UNAME_STAND_IN, RequestResults
from SpotifyAccess import AddSongToPlaylist


@DISCORD_CLIENT.event
# pylint: disable-next:invalid-name
async def on_ready():
    print(f"Logged in as a bot {DISCORD_CLIENT.user}")


@DISCORD_CLIENT.event
# pylint: disable-next:invalid-name
async def on_message(message):
    username = str(message.author).split("#", maxsplit=1)[0]
    channel = str(message.channel.name)
    isTesting = "testing" in channel
    logged = False

    if await HandleCommands(message, isTesting):
        return

    if playlistID := CONFIG["Channel Maps"].get(channel, None):
        for trackID in re.findall(
            r"https://open.spotify.com/track/([a-zA-Z0-9]+)", message.content
        ):
            status = RequestResults.Failed
            status, errMessage, trackInfo = AddSongToPlaylist(trackID, playlistID, isTesting)
            if status != RequestResults.Added:
                await message.channel.send(
                    f"An Error Occurred: {errMessage.replace(UNAME_STAND_IN, username)}"
                )
            await LogUserData(trackInfo, username, status, isTesting)
            logged = True

        if not logged and "open.spotify" in message.content:
            await message.channel.send(
                f"@{username}, I think that was a spotify link but I couldn't figure it as a track"
            )
            await LogUserData(
                (message.content, "", ""), username, RequestResults.RegexFail, isTesting
            )


if __name__ == "__main__":
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
