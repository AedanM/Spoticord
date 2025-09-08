import re
from itertools import islice

from Defines import CONFIG, GetMemory, GetUserData, SaveMemory


def Chunk(toBeSplit, chunkSize) -> list:
    toBeSplit = iter(toBeSplit)
    return list(iter(lambda: tuple(islice(toBeSplit, chunkSize)), ()))


async def SendMessage(output, contextObj, reply: bool = False, useChannel: bool = False) -> None:
    memory = await GetMemory()
    channelId = contextObj.channel.id if not useChannel else contextObj.id
    for message in Chunk(output, 2000):
        message = "".join(message)
        if useChannel:
            await contextObj.send(message)
        else:
            await (contextObj.reply(message) if reply else contextObj.channel.send(message))

    if memory["LastChannel"] != channelId:
        memory["LastChannel"] = str(channelId)
        await SaveMemory()


async def DadMode(message) -> None:
    for dadCommand in CONFIG["DadCommands"]:
        if subject := re.search(dadCommand["regex"], message.content.lower()):
            subject = subject.group(1)
            await SendMessage(
                dadCommand["response"].replace("{subject}", subject), message, reply=True
            )


async def NotifyPlaylistLength(response) -> None:
    playlistLen = len([x for x in await GetUserData() if x.EntryStatus.WasSuccessful])
    if playlistLen % CONFIG["UpdateInterval"] == 0:
        await SendMessage(f"This was song #{playlistLen} 🙌", response, reply=True)

    return


async def TimeToSec(time) -> int:
    return (time.hour * 60 + time.minute) * 60 + time.second
