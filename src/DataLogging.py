from datetime import datetime

from Defines import UNAME_STAND_IN, AppendUserData, LoadUserData, Status


async def LogUserData(
    trackInfo: tuple[str, str, str, str],
    user: str,
    status: Status,
    isTesting,
) -> None:
    message = f"\n{datetime.now()},{user},{status},{','.join([f'"{x}"' for x in trackInfo])}"
    if isTesting and status != Status.ForceAdd:
        print(message)
    else:
        AppendUserData(message)
        await LoadUserData()


def GetResponse(result: Status, username: str, isTesting: bool) -> str:
    s = ""
    match result:
        case Status.Repeat:
            s = (
                "Already in the playlist, @everyone mock them"
                if not isTesting
                else "Try again bucko, already added"
            )
        case Status.BadVibes:
            s = f"@{UNAME_STAND_IN} You failed the Pedo Check. Reconsider your choices"
        case Status.WrongMarket:
            s = "Track not available in the UK, sorry."
        case Status.Failed:
            s = "You generated an exception with that one 😡, thanks numbnuts"
        case Status.RegexFail:
            s = f"@{UNAME_STAND_IN}, I think that was a spotify link but I couldn't figure it as a track"
        case Status.Added:
            s = ""
        case Status.ForceAdd:
            s = "This was forcefully added, I hope you know what you're doing..."
    return s.replace(UNAME_STAND_IN, username)
