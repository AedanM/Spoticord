"""Handle Logging Data."""

from datetime import datetime

from Defines import UNAME_STAND_IN, AppendUserData, LoadUserData, Status, UserDataEntry


async def LogUserData(
    trackInfo: tuple[str, str, str, str],
    user: str,
    status: Status,
    isTesting: bool,
    bonus: str = "",
) -> None:
    """Write user data to a file.

    Args:
        trackInfo (tuple[str, str, str, str]): tuple of identity Information
        user (str): username of who added track
        status (Status): Summary of attempt to add track
        isTesting (bool): is this in a production channel?
    """
    entry = UserDataEntry(
        TimeAdded=datetime.now(),
        User=user,
        EntryStatus=status,
        TrackId=trackInfo[0],
        TrackName=trackInfo[1],
        Artist=trackInfo[2],
        URI=trackInfo[3],
        Bonus=bonus,
    )
    if isTesting and status != Status.ForceAdd:
        print(entry)
    else:
        AppendUserData(entry)
        await LoadUserData()


async def LogEntry(
    entry: UserDataEntry,
    isTesting: bool,
    bonus: str = "",
) -> None:
    """Write user data to a file."""
    AppendUserData(entry)
    await LoadUserData()


def GetResponse(result: Status, username: str, isTesting: bool) -> str:
    """Get the response string for different status events.

    Args:
        result (Status): result of attempt to add to playlist
        username (str): username of person who attempted
        isTesting (bool): are we in a production channel

    Returns
    -------
        str: response to status event
    """
    s: str = ""
    match result:
        case Status.Repeat:
            s = (
                f"Already in the playlist (added by {username}), @everyone mock this duplicate"
                if not isTesting
                else "Try again bucko, already added"
            )
        case Status.BadVibes:
            s = f"@{UNAME_STAND_IN} You failed the Pedo Check. Reconsider your choices"
        case Status.WrongMarket:
            s = "Track not available in the UK, sorry."
        case Status.Failed:
            s = "You generated an exception with that one 😡, thanks numb nuts"
        case Status.RegexFail:
            s = f"@{UNAME_STAND_IN}, I think that was a spotify link but I couldn't figure it"
        case Status.Added:
            s = ""
        case Status.ForceAdd:
            s = "This was forcefully added, I hope you know what you're doing..."
    return s.replace(UNAME_STAND_IN, username)
