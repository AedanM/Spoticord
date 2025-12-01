"""Graphing functions for playlist data."""

import inspect
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.io as pio
from discord import Message

from Defines import CONFIG, MASTER_GENRES, TEMP_USER_DATA_FILE, USER_DATA_FILE, Status
from SpotifyAccess import GetFullInfo

GRAPHS: list[str] = [
    "userPopularity",
    "totalAverage",
    "popularity",
    "progress",
    "users",
    "totals",
    "heat",
    "unique",
    "genres",
]


async def GraphDurations(valid: pd.DataFrame) -> Any:
    """Generate a histogram of track durations."""
    durations = []
    for track in valid["track"]:
        info = await GetFullInfo(str(track))
        duration_ms = info["track"].get("duration_ms", 0)
        durations.append(duration_ms / 60000)  # Convert to minutes
    valid = valid.copy()
    valid["duration_minutes"] = durations
    fig = px.box(
        valid,
        x="duration_minutes",
        y="user",
        orientation="h",
        points="all",
        color="user",
        title="Track Duration Distribution",
        labels={"duration_minutes": "Duration (minutes)"},
        color_discrete_map=CONFIG["UserColors"],
    )
    fig.update_layout(boxmode="group")
    return fig


async def GraphGenres(valid: pd.DataFrame) -> Any:
    """Generate a pie chart of genre distribution."""
    genreFreq = dict.fromkeys([*MASTER_GENRES, "Other"], 0)
    for track in valid["track"]:
        trackInfo = await GetFullInfo(str(track))
        genres = "".join(trackInfo["artist"].get("genres", []))
        matched = False
        for genre in MASTER_GENRES:
            if genre in "".join(genres):
                genreFreq[genre] += 1
                matched = True
        if not matched:
            genreFreq["Other"] += 1

    fig = px.pie(
        names=list(genreFreq.keys()),
        values=list(genreFreq.values()),
        title="Genre Distribution",
        color_discrete_sequence=px.colors.qualitative.Light24,
    )
    fig.update_layout(showlegend=False)
    fig.update_traces(
        textinfo="label+percent",
        textposition="inside",
    )
    return fig


async def GraphTimeline(valid: pd.DataFrame) -> Any:
    """Generate a timeline graph of when tracks were released."""
    release_dates = []
    for track in valid["track"]:
        info = await GetFullInfo(str(track))
        date_str = info["track"]["album"].get("release_date", "")
        match = re.match(r"(\d+)-?(\d*)-?(\d*)", date_str)
        if match:
            year, month, day = [int(x) if x.isnumeric() and x else 1 for x in match.groups()]
            release = date(year=year, month=month, day=day)
        else:
            release = date.today()
        release_dates.append(release.isoformat())
    valid = valid.copy()
    valid["release_date"] = release_dates
    return px.box(
        valid,
        y="user",
        x="release_date",
        orientation="h",
        color="user",
        points="all",
        color_discrete_map=CONFIG["UserColors"],
    )


def UserTrackNum(frame: pd.DataFrame, track: str) -> int:
    """Get the number of tracks a user has added before this one."""
    trackRow = frame.loc[frame["track"] == track]
    if trackRow.empty:
        return 0
    trackIDx = trackRow.index[0]
    user = trackRow["user"].iloc[0]
    prevEntries = frame.loc[(frame["user"] == user) & (frame.index < trackIDx)]
    return len(prevEntries)


async def PopularityRanking(track: str, useFollowers: bool = False) -> float:
    """Calculate a popularity ranking for a track."""
    try:
        trackInfo = await GetFullInfo(track)
        if not useFollowers:
            val = 0.75 * trackInfo["track"].get("popularity", 0) + 0.25 * trackInfo["artist"].get(
                "popularity", 0
            )
        else:
            val = trackInfo["artist"].get("followers", {}).get("total", 0)
    except (KeyError, TypeError):
        val = -1.0
    return val


def AvgPopularityAtRow(frame: pd.DataFrame, row: int, useFollowers: bool = False) -> float:
    """Average popularity of all tracks up to and including this one."""
    trackIdx = frame.index[row]
    prevEntries = frame.loc[:trackIdx]
    col = "popularity" if not useFollowers else "followers"
    if len(prevEntries) == 0:
        return 0.0
    return round(prevEntries[col].sum() / len(prevEntries), 2)


async def PrepDataFrame(saveFile: bool = False) -> pd.DataFrame:
    """Prepare the main dataframe with all calculated fields."""
    df = pd.read_csv(USER_DATA_FILE)

    df["popularity"] = [await PopularityRanking(x) for x in df["track"]]
    df["followers"] = [await PopularityRanking(x, True) for x in df["track"]]
    df["userCount"] = [UserTrackNum(df, x) for x in df["track"]]
    df["average"] = [AvgPopularityAtRow(df, i) for i in range(len(df))]
    df["followers_average"] = [AvgPopularityAtRow(df, i, True) for i in range(len(df))]

    if saveFile:
        # Reset index and ensure columns are in the correct order before saving
        df_reset = df.reset_index(drop=True)
        # Convert any list-like columns to semicolon-separated strings for CSV output
        for col in df_reset.columns:
            if df_reset[col].apply(lambda x: isinstance(x, list | pd.Series)).any():
                df_reset[col] = df_reset[col].apply(
                    lambda x: ";".join(map(str, x)) if isinstance(x, list | pd.Series) else x,
                )
        df_reset.to_csv(TEMP_USER_DATA_FILE, sep=",", encoding="utf-8", index=False)

    return df


def GetUniqueRatio(data: pd.DataFrame) -> float:
    """Get the ratio of unique items in a list."""
    return len(set(data)) / len(data) if len(data) > 1 else 0.0


async def PrepUserData(df: pd.DataFrame, saveFile: bool = False) -> pd.DataFrame:
    """Prepare the user-specific dataframe with all calculated fields."""
    user_names = df["user"].unique()
    users = pd.DataFrame({"names": user_names})
    user_group = df.groupby("user")
    users["artists"] = users["names"].map(
        lambda user: user_group.get_group(user)["artist"].tolist(),
    )
    users["count"] = users["names"].map(
        lambda user: len(user_group.get_group(user)),
    )

    genres_list = []
    for user in users["names"]:
        genres = []
        for track in user_group.get_group(user)["track"]:
            info = await GetFullInfo(track)
            genres.extend(info["artist"].get("genres", []))
        genres_list.append(genres)
    users["genres"] = genres_list
    users["playlist_%"] = users["count"] / len(df)
    users["genre_ratio"] = users["genres"].apply(GetUniqueRatio)
    users["artist_ratio"] = users["artists"].apply(GetUniqueRatio)
    users["median_popularity"] = users["names"].map(
        lambda user: user_group.get_group(user)["popularity"].median(),
    )
    users["average_popularity"] = users["names"].map(
        lambda user: user_group.get_group(user)["popularity"].mean(),
    )

    users["overall_score"] = (
        users["playlist_%"]
        + users["artist_ratio"]
        + users["genre_ratio"]
        - (abs(50 - users["median_popularity"]) / 50)
    )

    if saveFile:
        # Convert 'artists' and 'genres' columns to semicolon-separated strings for CSV output
        users_out = users.copy()
        users_out["artists"] = users_out["artists"].apply(lambda x: ";".join(map(str, x)))
        users_out["genres"] = users_out["genres"].apply(lambda x: ";".join(map(str, x)))
        users_out.to_csv(TEMP_USER_DATA_FILE, sep=",", encoding="utf-8", index=False)

    return users


async def Graphs(message: Message) -> list[Path]:
    """Generate graphs based on user data and message content."""
    full = await PrepDataFrame()
    if "result" not in full.columns:
        raise ValueError("'result' column not found in user data.")

    def WasAdded(r: str) -> bool:
        try:
            return Status(r).WasSuccessful
        except Exception:
            return False

    playlistID = CONFIG["Channel Maps"].get(message.channel.name, None)
    valid = full.loc[full["result"].apply(WasAdded)]
    valid = full.loc[full["playlistID"] == playlistID]

    if isinstance(valid, pd.Series):
        return []
    users = await PrepUserData(valid)

    valid.reset_index(drop=True)
    useFollowers = " followers" in message.content
    graphs: dict[str, Callable] = {
        "popularity": lambda: px.scatter(
            valid,
            x=valid.index,
            y="popularity" if not useFollowers else "followers",
            color="user",
            trendline="lowess",
            log_y=useFollowers,
            color_discrete_map=CONFIG["UserColors"],
        ),
        "userPopularity": lambda: px.scatter(
            valid,
            x="userCount",
            y="popularity" if not useFollowers else "followers",
            color="user",
            log_y=useFollowers,
            trendline="lowess",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "totalAverage": lambda: px.scatter(
            valid,
            x=valid.index,
            y="average" if not useFollowers else "followers_average",
            log_y=useFollowers,
            trendline="lowess",
        ),
        "progress": lambda: px.scatter(
            valid,
            x="time",
            y=valid.index,
            color="user",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "users": lambda: px.pie(
            users,
            names="names",
            values="count",
            color="names",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "unique_artists": lambda: px.bar(
            users,
            x="names",
            y="artist_ratio",
            color="names",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "unique_genres": lambda: px.bar(
            users,
            x="names",
            y="genre_ratio",
            color="names",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "rating": lambda: px.bar(
            users,
            x="names",
            y="overall_score",
            color="names",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "totals": lambda: px.box(
            valid,
            x="user",
            log_y=useFollowers,
            y="popularity" if not useFollowers else "followers",
            color="user",
            color_discrete_map=CONFIG["UserColors"],
            points="all",
        ),
        "heat": lambda: px.density_heatmap(
            valid,
            x=valid.index,
            y="popularity",
            nbinsx=50,
            nbinsy=10,
        ),
        "genres": GraphGenres,
        "timeline": GraphTimeline,
        "duration": GraphDurations,
    }
    (USER_DATA_FILE.parent / "graphs").mkdir(exist_ok=True)
    made: list[Path] = []
    found: list[Path] = []
    figs: list = []
    for graph, func in graphs.items():
        if graph in message.content or " all" in message.content:
            dst = (
                USER_DATA_FILE.parent / "graphs" / f"{graph}_{valid.shape[0]}x{valid.shape[1]}.png"
            )
            if dst.exists():
                found.append(dst)
            else:
                _ = [x.unlink() for x in (USER_DATA_FILE.parent / "graphs").glob(f"{graph}_*")]
                if inspect.iscoroutinefunction(func):
                    figs.append(await func(valid))
                else:
                    figs.append(func())
                figs[-1].update_layout(xaxis={"categoryorder": "total ascending"})
                made.append(dst)
    pio.write_images(fig=figs, file=made, width=960, height=540, scale=2)
    return found + made
