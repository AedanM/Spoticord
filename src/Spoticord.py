import re

from DataLogging import LogUserData
from Defines import CONFIG, DISCORD_CLIENT, RequestResults
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

    if linkMatch := re.match(r"https:\/\/open\.spotify\.com\/track\/([^?\s]*)", message.content):
        trackID = linkMatch.group(1)
        playlistID = CONFIG["Channel Maps"].get(channel, None)
        status = RequestResults.Failed
        if playlistID is None:
            await message.channel.send(f"No playlist configured for {channel}")
        else:
            status, errMessage, trackInfo = AddSongToPlaylist(trackID, playlistID)
            if status != RequestResults.Added:
                await message.channel.send(f"An Error Occurred: {errMessage}")
            await LogUserData(trackInfo, username, status)


if __name__ == "__main__":
    DISCORD_CLIENT.run(CONFIG["DiscordToken"])
