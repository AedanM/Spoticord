"""Functions to get stats."""

from discord import Message

from Defines import GetMemory, GetUserData, UserDataEntry
from SpotifyAccess import GetFullInfo
from Utility import SendMessage

STAT_COUNT: int = 5


async def UserStats(message: Message) -> None:
    """Get statistics for track additions.

    Args:
        message (Message): triggering message
    """
    data: list[UserDataEntry] = await GetUserData()
    useReverse: bool = "reverse" not in message.content
    username: str = str(message.author).split("#", maxsplit=1)[0]
    outStr: str = ""
    if "duration" in message.content:
        outStr = await GetDuration(data, useReverse)
    if "poster" in message.content:
        outStr = await GetPosterCount(data)
    if "mainstream" in message.content:
        if "artist" in message.content:
            outStr = await GetMainstreamArtists(
                data,
                username,
                useReverse,
                "follower" in message.content,
            )
        else:
            outStr = await GetMainstreamRating(
                data,
                useReverse,
                "follower" in message.content,
            )
    if "artist" in message.content:
        outStr = await GetArtistCount(data, useReverse)
    if "genre" in message.content:
        outStr = await GetGenreCount(data, useReverse)
    if "unlabeled" in message.content:
        mem = await GetMemory()
        artists = [x for x in mem["Cache"]["artists"].values() if x["genres"] == []]
        outStr = "Missing Genres:\n" + "\n".join([x["name"] for x in artists])
    if "popularity" in message.content:
        outStr = await GetPopularityRanking(
            data,
            useReverse,
            "follower" in message.content,
        )

    if outStr:
        await SendMessage(outStr, message, reply=True)


async def GetPopularityRanking(
    data: list[UserDataEntry],
    useReverse: bool,
    useFollowers: bool,
) -> str:
    """Get data for who most popular artists are.

    Parameters
    ----------
    data : list[UserDataEntry]
        entry data
    useReverse: bool
        flip data
    useFollowers: bool
        use follower data instead

    Returns
    -------
    str
        result str
    """
    popularity = {}
    for track in [x for x in data if x.EntryStatus.WasSuccessful]:
        trackInfo = await GetFullInfo(track.TrackId)
        if trackInfo["artist"]["name"] not in popularity:
            popularity[trackInfo["artist"]["name"]] = (
                trackInfo["artist"]["popularity"]
                if not useFollowers
                else trackInfo["artist"]["followers"]["total"]
            )
    popularity = sorted(popularity.items(), key=lambda x: x[1], reverse=useReverse)
    popularity = (
        [x for x in popularity if x[1] >= popularity[STAT_COUNT][1]]
        if useReverse
        else [x for x in popularity if x[1] <= popularity[STAT_COUNT][1]]
    )
    if len(popularity) > 2 * STAT_COUNT:
        popularity = popularity[: 2 * STAT_COUNT]

    return "Popularity Rankings:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in popularity])


async def GetGenreCount(
    data: list[UserDataEntry],
    useReverse: bool,
) -> str:
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
    genreFreq = [
        x for x in sorted(genreFreq.items(), key=lambda x: x[1], reverse=useReverse) if x[1] > 1
    ]
    genreFreq = (
        [x for x in genreFreq if x[1] >= genreFreq[STAT_COUNT][1]]
        if useReverse
        else [x for x in genreFreq if x[1] <= genreFreq[STAT_COUNT][1]]
    )
    if len(genreFreq) > 2 * STAT_COUNT:
        genreFreq = genreFreq[: 2 * STAT_COUNT]
    return "Top Genres:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in genreFreq])


async def GetArtistCount(
    data: list[UserDataEntry],
    useReverse: bool,
) -> str:
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
    addFreq = sorted(addFreq.items(), key=lambda x: x[1], reverse=useReverse)
    addFreq = (
        [x for x in addFreq if x[1] >= addFreq[STAT_COUNT][1]]
        if useReverse
        else [x for x in addFreq if x[1] <= addFreq[STAT_COUNT][1]]
    )
    if len(addFreq) > 2 * STAT_COUNT:
        addFreq = addFreq[: 2 * STAT_COUNT]
    return "Top Artists:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])


async def GetMainstreamRating(
    data: list[UserDataEntry],
    useReverse: bool,
    useFollowers: bool,
) -> str:
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
    cool = sorted(results.items(), key=lambda x: x[1], reverse=useReverse)
    return "Mainstream Ratings:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in cool])


async def GetMainstreamArtists(
    data: list[UserDataEntry],
    user: str,
    useReverse: bool,
    useFollowers: bool,
) -> str:
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
        if info["artist"]["name"] not in results:
            results[info["artist"]["name"]] = (
                info["artist"]["popularity"]
                if not useFollowers
                else info["artist"]["followers"]["total"]
            )
    popularityRanking = sorted(results.items(), key=lambda x: x[1], reverse=useReverse)
    popularityRanking = (
        [x for x in popularityRanking if x[1] >= popularityRanking[STAT_COUNT][1]]
        if useReverse
        else [x for x in popularityRanking if x[1] <= popularityRanking[STAT_COUNT][1]]
    )
    if len(popularityRanking) > 2 * STAT_COUNT:
        popularityRanking = popularityRanking[: 2 * STAT_COUNT]
    return f"Mainstream Artists for {user}:\n" + "\n".join(
        [f"{x[0]}: {x[1]}" for x in popularityRanking],
    )


async def GetPosterCount(data: list[UserDataEntry]) -> str:
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
    addFreq = sorted(addFreq.items(), key=lambda x: x[1], reverse=True)
    return "Top Posters:\n" + "\n".join([f"{x[0]}: {x[1]}" for x in addFreq])


async def GetDuration(data: list[UserDataEntry], useReverse: bool) -> str:
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

    return f"{'Shortest' if useReverse else 'Longest'}:\n- " + "\n- ".join(
        [
            f"{x[1] / 1000} seconds -> {x[0].TrackInfo}"
            for x in (sortedTimes[:5] if useReverse else reversed(sortedTimes[-5:]))
        ],
    )
