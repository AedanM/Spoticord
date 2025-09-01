"""Functions to get stats."""

import re

from discord import Message

from Defines import GetMemory, GetUserData, UserDataEntry
from SpotifyAccess import GetFullInfo
from Utility import SendMessage

STAT_COUNT: int = 10


async def FilterData(message: Message, data: list[list]) -> list:
    """Perform common filtering of data."""
    out = data
    statCount = STAT_COUNT
    if match := re.search(r"\s[Tt](\d+)", message.content):
        statCount = int(match.group(1))
    if "reverse" not in message.content:
        out = list(reversed(out))
    if statCount < len(out):
        out = out[:statCount]
    return out


async def UserStats(message: Message) -> None:
    """Get statistics for track additions.

    Args:
        message (Message): triggering message
    """
    data: list[UserDataEntry] = await GetUserData()
    stats: list = []
    username: str = str(message.author).split("#", maxsplit=1)[0]
    outStr: str = ""
    if "duration" in message.content:
        outStr, stats = await GetDuration(data)
    if "poster" in message.content:
        outStr, stats = await GetPosterCount(data)
    if "genre" in message.content:
        outStr, stats = await GetGenreCount(data)
    if "unlabeled" in message.content:
        mem = await GetMemory()
        artists = [x for x in mem["Cache"]["artists"].values() if x["genres"] == []]
        outStr = "Missing Genres:\n" + "\n".join([x["name"] for x in artists])
    if "popularity" in message.content:
        outStr, stats = await GetPopularityRanking(
            data,
            "follower" in message.content,
            "track" in message.content,
        )

    if "mainstream" in message.content and "personal" in message.content:
        outStr, stats = await GetPersonalMainstream(
            data,
            username,
            "follower" in message.content,
            "track" in message.content,
        )
    elif "mainstream" in message.content:
        outStr, stats = await GetMainstreamRating(
            data,
            "follower" in message.content,
        )
    elif "artist" in message.content:
        outStr, stats = await GetArtistCount(data)

    stats = await FilterData(message, stats)
    outStr = f"{outStr}\n{'\n'.join([f'{x[0]}: {x[1]}' for x in stats])}"
    if outStr:
        await SendMessage(outStr, message, reply=True)


async def GetPopularityRanking(
    data: list[UserDataEntry],
    useFollowers: bool,
    useTracks: bool,
) -> tuple[str, list]:
    """Get data for who most popular artists/tracks are.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data
    useFollowers: bool
        use follower data instead
    useTracks: bool
        use track data instead

    Returns
    -------
    str
        result str
    """
    popularity = {}
    for track in [x for x in data if x.EntryStatus.WasSuccessful]:
        trackInfo = await GetFullInfo(track.TrackId)
        if trackInfo["artist"]["name"] not in popularity:
            if not useTracks:
                popularity[trackInfo["artist"]["name"]] = (
                    trackInfo["artist"]["popularity"]
                    if not useFollowers
                    else trackInfo["artist"]["followers"]["total"]
                )
            else:
                popularity[track.TrackInfo] = (0.75 * trackInfo["track"]["popularity"]) + (
                    0.25 * trackInfo["artist"]["popularity"]
                )

    return "Popularity Rankings:", sorted(popularity.items(), key=lambda x: x[1])


async def GetGenreCount(
    data: list[UserDataEntry],
) -> tuple[str, list]:
    """Get data for how many genre was added.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data

    Returns
    -------
    str
        result str
    """
    genres: list[str] = []
    for track in [x for x in data if x.EntryStatus.WasSuccessful]:
        genres += (await GetFullInfo(track.TrackId))["artist"]["genres"]
    genreFreq = {x: genres.count(x) for x in set(genres)}
    genreFreq = [x for x in sorted(genreFreq.items(), key=lambda x: x[1]) if x[1] > 1]
    return "Genre Frequency:", genreFreq


async def GetArtistCount(
    data: list[UserDataEntry],
) -> tuple[str, list]:
    """Get data for how many times an artist was added.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data

    Returns
    -------
    str
        result str
    """
    addedSongs: list[UserDataEntry] = [x for x in data if x.EntryStatus.WasSuccessful]
    addFreq = {
        artist: len([entry for entry in addedSongs if entry.Artist == artist])
        for artist in {x.Artist for x in data}
    }
    addFreq = sorted(addFreq.items(), key=lambda x: x[1])
    addFreq = [x for x in addFreq if x[0] != 0]
    return "Artist Frequency", addFreq


async def GetMainstreamRating(
    data: list[UserDataEntry],
    useFollowers: bool,
) -> tuple[str, list]:
    """Get data for who the most mainstream poster is.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data
    useFollowers: bool
        flip data

    Returns
    -------
    str
        result str
    """
    results = {}
    for uname in {x.User for x in data}:
        totalSongs = 0
        totalPopularity = 0
        for entry in [x for x in data if x.EntryStatus.WasSuccessful and x.User == uname]:
            t = await GetFullInfo(entry.TrackId)
            totalPopularity += (
                t["artist"]["popularity"] if not useFollowers else t["artist"]["followers"]["total"]
            )
            totalSongs += 1
        if totalSongs != 0:
            results[uname] = round(totalPopularity / totalSongs, 2)
    return "Mainstream Ratings:", sorted(results.items(), key=lambda x: x[1])


async def GetPersonalMainstream(
    data: list[UserDataEntry],
    user: str,
    useFollowers: bool,
    useTracks: bool,
) -> tuple[str, list]:
    """Get data for who the user's most mainstream artists.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    user:
        user who requested data
    useReverse: bool
        flip data
    useFollowers: bool
        flip data

    Returns
    -------
    str
        result str
    """
    results = {}
    for entry in [x for x in data if x.EntryStatus.WasSuccessful and x.User == user]:
        info = await GetFullInfo(entry.TrackId)
        if useTracks:
            results[entry.TrackInfo] = (0.75 * info["track"]["popularity"]) + (
                0.25 * info["artist"]["popularity"]
            )
        else:
            if info["artist"]["name"] not in results:
                results[info["artist"]["name"]] = (
                    info["artist"]["popularity"]
                    if not useFollowers
                    else info["artist"]["followers"]["total"]
                )
    return f"Mainstream Artists for {user}:", sorted(results.items(), key=lambda x: x[1])


async def GetPosterCount(data: list[UserDataEntry]) -> tuple[str, list]:
    """Get data for how many songs a user added.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data

    Returns
    -------
    str
        result str
    """
    addFreq = {
        uname: len(
            [
                entry
                for entry in [y for y in data if y.EntryStatus.WasSuccessful]
                if entry.User == uname
            ],
        )
        for uname in {x.User for x in data}
    }
    addFreq = sorted(addFreq.items(), key=lambda x: x[1])
    return "Song Posters:", addFreq


async def GetDuration(data: list[UserDataEntry]) -> tuple[str, list]:
    """Get data for how the longest/shortest song.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data

    Returns
    -------
    str
        result str
    """
    timed: dict[UserDataEntry, int] = {}
    for song in [x for x in data if x.EntryStatus.WasSuccessful]:
        info = await GetFullInfo(song.TrackId)
        timed[song] = info["track"]["duration_ms"]
    sortedTimes: list[tuple[UserDataEntry, int]] = sorted(
        timed.items(),
        key=lambda x: x[1],
    )
    return "Track Duration (s):", [[round(x[1] / 1000), x[0].TrackInfo] for x in sortedTimes]
