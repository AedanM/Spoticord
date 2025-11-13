"""Functions to get stats."""

import math
import re
from statistics import quantiles
from typing import Any

import pandas as pd
from discord import Message

from Defines import CONFIG, GetMemory, GetUserData, Status, UserDataEntry
from Graphing import PrepDataFrame, PrepUserData
from SpotifyAccess import GetFullInfo
from Utility import SendMessage

STAT_COUNT: int = 10


async def FilterData(message: Message, results: dict) -> dict:
    """Perform common filtering of data."""
    out: dict = results["Data"]
    statCount = STAT_COUNT
    if countMatch := re.search(r"\s[Tt](\d+)", message.content):
        statCount = int(countMatch.group(1))
    if userMatch := re.search(r"\suser:([^ ]+)", message.content):
        username = userMatch.group(1)
        out = {entry: value for entry, value in out.items() if entry.User == username}
    if genreMatch := re.search(r"\sgenre:\"?([^\"]+)\"?", message.content):
        genre = genreMatch.group(1)
        trimmed = out.copy()
        for entry in out:
            info = await GetFullInfo(entry.TrackId)
            if genre in info["artist"]["genres"]:
                pass
            else:
                del trimmed[entry]
        out = trimmed
    sortedTuples = sorted(out.items(), key=lambda x: x[1], reverse="reverse" not in message.content)
    if statCount < len(sortedTuples):
        sortedTuples = sortedTuples[:statCount]
    results["Filtered"] = sortedTuples
    return results


async def GetReleaseDate(data: list[UserDataEntry]) -> dict:
    """Get data for when songs were released."""

    async def Formatter(entry: UserDataEntry, data: Any) -> str:
        return f"{data} -> {entry.TrackInfo} added by {entry.User}"

    output = {}
    for entry in [x for x in data if x.EntryStatus.WasSuccessful]:
        info = await GetFullInfo(entry.TrackId)
        releaseDate = info["track"]["album"]["release_date"]
        output[entry] = releaseDate

    return {
        "Title": "Release Dates",
        "Formatter": Formatter,
        "Data": output,
    }


async def GetDuration(data: list[UserDataEntry]) -> dict:
    """Get data for how the longest/shortest song."""
    timed: dict[UserDataEntry, int] = {}
    for song in [x for x in data if x.EntryStatus.WasSuccessful]:
        info = await GetFullInfo(song.TrackId)
        timed[song] = info["track"]["duration_ms"]

    async def Formatter(entry: UserDataEntry, data: Any) -> str:
        timeStr = f"{math.floor(data / 60000):02d}:{round((data % 60000) / 1000):02d}"
        return f"{timeStr} - {entry.TrackInfo} added by {entry.User}"

    return {
        "Title": "Track Duration (min)",
        "Formatter": Formatter,
        "Data": timed,
    }


async def GetEntryPopularity(data: list[UserDataEntry]) -> dict:
    """Get popularity for entries."""
    output = {}
    for entry in [x for x in data if x.EntryStatus.WasSuccessful]:
        info = await GetFullInfo(entry.TrackId)
        output[entry] = info["track"]["popularity"]

    async def Formatter(entry: UserDataEntry, data: Any) -> str:
        return f"{data} -> {entry.TrackInfo} added by {entry.User}"

    return {
        "Title": "Entry Popularity",
        "Formatter": Formatter,
        "Data": output,
    }


async def GetRecent(data: list[UserDataEntry]) -> dict:
    """Get most recent additions."""
    output = {}
    for entry in [x for x in data if x.EntryStatus.WasSuccessful]:
        output[entry] = entry.TimeAdded

    async def Formatter(entry: UserDataEntry, data: Any) -> str:
        timeStr = data.strftime("%Y-%m-%d %H:%M")
        return f"{timeStr} - {entry.TrackInfo} added by {entry.User}"

    return {
        "Title": "Recent Additions",
        "Formatter": Formatter,
        "Data": output,
    }


# region SpecialCases
async def GetUnlabeled() -> dict:
    """Get non genre-ed artists."""
    mem = await GetMemory()
    artists = [x for x in mem["Cache"]["artists"].values() if x["genres"] == []]
    return {
        "Title": "Missing Genres",
        "Data": dict.fromkeys(artists, None),
        "Formatter": lambda x: x["name"],
    }


async def GetOnTheList() -> dict:
    """Return the current list."""
    mem = await GetMemory()
    artistInfo = mem["Cache"]["artists"]
    out = []
    for artistID, rating in CONFIG["Vibes"].items():
        artist = artistInfo.get(artistID, None)
        out.append((artist["name"] if artist else artistID, float(rating)))
    return {"Title": "On The List", "Formatter": lambda x: x[0], "Data": out}


# endregion


async def UserStats(message: Message) -> None:
    """Get statistics for track additions.

    Args:
        message (Message): triggering message
    """
    data: list[UserDataEntry] = await GetUserData()
    result: dict = {}
    outStr: str = ""

    handlers: dict = {
        "popularity": lambda: GetEntryPopularity(data),
        "release": lambda: GetReleaseDate(data),
        "duration": lambda: GetDuration(data),
        "recent": lambda: GetRecent(data),
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
            result: dict = await handler()
            break
    result = await FilterData(message, result)
    outStr = (
        f"{result['Title']}:\n"
        f"{'\n'.join([await result['Formatter'](entry, data) for entry, data in result['Filtered']])}"
    )
    if outStr:
        await SendMessage(outStr, message, reply=True)


"""# "onTheList": lambda: GetOnTheList(),
        # "duration": lambda: GetDuration(data),
        # "poster": lambda: GetPosterCount(data),
        # "genre": lambda: GetGenreCount(data),
        # "unlabeled": lambda: GetUnlabeled(),
        # "release": lambda: GetReleaseDate(data),
        # "popularity": lambda: GetPopularityRanking(
        #     data,"onTheList": lambda: GetOnTheList(),
        # "duration": lambda: GetDuration(data),
        # "poster": lambda: GetPosterCount(data),
        # "genre": lambda: GetGenreCount(data),
        # "unlabeled": lambda: GetUnlabeled(),
        # "release": lambda: GetReleaseDate(data),
        # "popularity": lambda: GetPopularityRanking(
        #     data,
        #     "follower" in message.content,
        #     "track" in message.content,
        # ),
        # "mainstream personal": lambda: GetPersonalMainstream(
        #     data,
        #     username,
        #     "follower" in message.content,
        #     "track" in message.content,
        # ),
        # "mainstream": lambda: GetMainstreamRating(
        #     data,
        #     "follower" in message.content,
        #     "median" in message.content,
        #     "quantiles" in message.content,
        # ),
        # "artist": lambda: GetArtistCount(data),
        # "users": lambda: GetUserInfo(
        #     data,
        #     message.content,
        #     "genres" in message.content,
        #     "artists" in message.content,
        #     re.search(r"genre=[^ ]+", message.content) is not None,
        # ),
        #     "follower" in message.content,
        #     "track" in message.content,
        # ),
        # "mainstream personal": lambda: GetPersonalMainstream(
        #     data,
        #     username,
        #     "follower" in message.content,
        #     "track" in message.content,
        # ),
        # "mainstream": lambda: GetMainstreamRating(
        #     data,
        #     "follower" in message.content,
        #     "median" in message.content,
        #     "quantiles" in message.content,
        # ),
        # "artist": lambda: GetArtistCount(data),
        # "users": lambda: GetUserInfo(
        #     data,
        #     message.content,
        #     "genres" in message.content,
        #     "artists" in message.content,
        #     re.search(r"genre=[^ ]+", message.content) is not None,
        # ),"""


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
        if genre := re.search(r"genre=([^\n]+)", message):
            genre = genre.group(1)
            tracks = [
                x for x in userData if genre in (await GetFullInfo(x.TrackId))["artist"]["genres"]
            ]
            out = [(x.TimeAdded.strftime("%Y-%m-%d %H:%M"), x.TrackInfo) for x in tracks]
    else:
        out = [(x.TimeAdded.strftime("%Y-%m-%d %H:%M"), x.TrackInfo) for x in userData]

    return "User Info:", out


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
