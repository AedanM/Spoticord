import re

from Defines import CONFIG, GetMemory, GetUserData, SaveMemory


async def SendMessage(output, contextObj, reply: bool = False, useChannel: bool = False):
    memory = await GetMemory()
    if useChannel:
        await contextObj.send(output)
        channelId = contextObj.id
    else:
        await (contextObj.reply(output) if reply else contextObj.channel.send(output))
        channelId = contextObj.channel.id

    if memory["LastChannel"] != channelId:
        memory["LastChannel"] = str(channelId)
        await SaveMemory()


async def DadMode(message):
    for dadCommand in CONFIG["DadCommands"]:
        if subject := re.search(dadCommand["regex"], message.content.lower()):
            subject = subject.group(1)
            await SendMessage(
                dadCommand["response"].replace("{subject}", subject), message, reply=True
            )


async def NotifyPlaylistLength(response):
    playlistLen = len([x for x in await GetUserData() if x.EntryStatus.WasSuccessful])
    if playlistLen % CONFIG["UpdateInterval"] == 0:
        await SendMessage(f"This was song #{playlistLen} 🙌", response, reply=True)

    return


async def TimeToSec(time) -> int:
    return (time.hour * 60 + time.minute) * 60 + time.second
