from datetime import datetime

import polars as pd
from Defines import CURRENT_USER_DATA, UNAME_STAND_IN, USER_DATA_FILE, USER_DATA_FILE_LOCK, Status


async def LogUserData(
    trackInfo: tuple[str, str, str],
    user: str,
    status: Status,
    isTesting,
) -> None:
    message = f"\n{datetime.now()},{user},{status},{','.join([f'"{x}"' for x in trackInfo])}"
    if isTesting:
        print(message)
    else:
        async with USER_DATA_FILE_LOCK:
            with USER_DATA_FILE.open(mode="a", encoding="utf-8") as fp:
                fp.write(message)
                # todo: make this more robust and less slow
                CURRENT_USER_DATA = pd.read_csv(USER_DATA_FILE)


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
