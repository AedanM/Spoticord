"""Functions to get stats."""

import math
import re
from sqlite3 import Time
from statistics import quantiles

import pandas as pd
from discord import Message

from Defines import CONFIG, GetMemory, GetUserData, Status, UserDataEntry
from Graphing import PrepDataFrame, PrepUserData
from SpotifyAccess import GetFullInfo
from Utility import SendMessage

STAT_COUNT: int = 10


async def FilterData(message: Message, data: list[tuple]) -> list:
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


async def GetReleaseDate(data: list[UserDataEntry]) -> tuple[str, list[tuple]]:
    """Get data for when songs were released.

    Parameters
    ----------
    data : list[UserDataEntry]
        input data

    Returns
    -------
    tuple[str, list[tuple]]
        result str and data
    """
    output: list[tuple] = []
    for row in [x for x in data if x.EntryStatus.WasSuccessful]:
        info = await GetFullInfo(row.TrackId)
        output.append((f"{row.User} - {row.TrackInfo}", info["track"]["album"]["release_date"]))

    return "Release Date:", sorted(output, key=lambda x: x[1])


async def UserStats(message: Message) -> None:
    """Get statistics for track additions.

    Args:
        message (Message): triggering message
    """
    data: list[UserDataEntry] = await GetUserData()
    stats: list = []
    username: str = str(message.author).split("#", maxsplit=1)[0]
    outStr: str = ""

    handlers: dict = {
        "onTheList": lambda: GetOnTheList(),
        "duration": lambda: GetDuration(data),
        "poster": lambda: GetPosterCount(data),
        "genre": lambda: GetGenreCount(data),
        "unlabeled": lambda: GetUnlabeled(),
        "release": lambda: GetReleaseDate(data),
        "popularity": lambda: GetPopularityRanking(
            data,
            "follower" in message.content,
            "track" in message.content,
        ),
        "mainstream personal": lambda: GetPersonalMainstream(
            data,
            username,
            "follower" in message.content,
            "track" in message.content,
        ),
        "mainstream": lambda: GetMainstreamRating(
            data,
            "follower" in message.content,
            "median" in message.content,
            "quantiles" in message.content,
        ),
        "artist": lambda: GetArtistCount(data),
        "users": lambda: GetUserInfo(
            data,
            message.content,
            "genres" in message.content,
            "artists" in message.content,
            re.search(r"genre=[^ ]+", message.content) is not None,
        ),
    }
    if message.content.split()[1] not in handlers:
        await SendMessage(
            "Valid keywords are: " + ", ".join([f"`{x}`" for x in handlers]),
            message,
            reply=True,
        )
        return
    for keyword, handler in handlers.items():
        if keyword in message.content.split()[1]:
            outStr, stats = await handler()
            break

    stats = await FilterData(message, stats)
    outStr = f"{outStr}\n{'\n'.join([f'{x[0]} -> {x[1]}' for x in stats])}"
    if outStr:
        await SendMessage(outStr, message, reply=True)


async def GetUnlabeled() -> tuple[str, list]:
    """Get non genre-ed artists."""
    mem = await GetMemory()
    artists = [x for x in mem["Cache"]["artists"].values() if x["genres"] == []]
    return "Missing Genres:", [x["name"] for x in artists]


async def GetUserInfo(
    data: list[UserDataEntry],
    message: str,
    useGenres: bool,
    useArtists: bool,
    getGenre: bool,
) -> tuple[str, list]:
    """Get user info."""
    out = []
    users = [x for x in message.split() if x.startswith("user:")]
    if not users:
        return "User Info:", []
    user = users[0].split("user:")[-1]
    userData = sorted(
        [x for x in data if x.EntryStatus.WasSuccessful and x.User == user],
        key=lambda x: x.TimeAdded,
    )
    print(user, userData)
    if useGenres:
        genres = []
        for d in userData:
            info = await GetFullInfo(d.TrackId)
            genres.extend(info["artist"]["genres"])
        genreFreq = {x: genres.count(x) for x in set(genres)}
        out = sorted(genreFreq.items(), key=lambda x: x[1])
    elif useArtists:
        artists = [x.Artist for x in userData]
        artistFreq = {x: artists.count(x) for x in set(artists)}
        out = sorted(artistFreq.items(), key=lambda x: x[1])
    elif getGenre:
        if genre := re.search(r"genre=([^ ]+)", message):
            genre = genre.group(1)
            tracks = [
                x for x in userData if genre in (await GetFullInfo(x.TrackId))["artist"]["genres"]
            ]
            out = [(x.TimeAdded.strftime("%Y-%m-%d %H:%M"), x.TrackInfo) for x in tracks]
    else:
        out = [(x.TimeAdded.strftime("%Y-%m-%d %H:%M"), x.TrackInfo) for x in userData]

    return "User Info:", out


async def GetOnTheList() -> tuple[str, list]:
    """Return the current list."""
    mem = await GetMemory()
    artistInfo = mem["Cache"]["artists"]
    out = []
    for artistID, rating in CONFIG["Vibes"].items():
        artist = artistInfo.get(artistID, None)
        out.append((artist["name"] if artist else artistID, float(rating)))
    return "On The List:", sorted(out, key=lambda x: x[1])


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
    genres: list[str] = [
        genre
        for track in [x for x in data if x.EntryStatus.WasSuccessful]
        for genre in (await GetFullInfo(track.TrackId))["artist"]["genres"]
    ]
    genreFreq = {x: genres.count(x) for x in set(genres)}
    return "Genre Frequency:", sorted(genreFreq.items(), key=lambda x: x[1])


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
    useMedian: bool,
    useQuantiles: bool,
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
    df = await PrepDataFrame()
    df = df.loc[df["result"] == Status.Added]
    if isinstance(df, pd.Series):
        return "Mainstream Ratings:", []
    users = await PrepUserData(df)
    for uname in {x.User for x in data}:
        if useQuantiles:
            popularity = []
            for entry in [x for x in data if x.EntryStatus.WasSuccessful and x.User == uname]:
                t = await GetFullInfo(entry.TrackId)
                popularity.append(
                    t["artist"]["popularity"]
                    if not useFollowers
                    else t["artist"]["followers"]["total"],
                )
                results[uname] = "[" + ", ".join([str(x) for x in quantiles(popularity)]) + "]"
        elif useMedian:
            results[uname] = users[users["names"] == uname]["median_popularity"].iloc[0]
        else:
            results[uname] = round(users[users["names"] == uname]["average_popularity"].iloc[0], 2)

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
    return f"Mainstream Data for {user}:", sorted(results.items(), key=lambda x: x[1])


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
    return "Track Duration (min):", [
        [f"{math.floor(x[1] / 60000):02d}:{round((x[1] % 60000) / 1000):02d}", x[0].TrackInfo]
        for x in sortedTimes
    ]
