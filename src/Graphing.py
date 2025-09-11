import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
from discord import Message

from Defines import CONFIG, TEMP_USER_DATA_FILE, USER_DATA_FILE, Status
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
]


def UserTrackNum(frame: pd.DataFrame, track: str) -> int:
    trackRow = frame.loc[frame["track"] == track]
    trackIDx = trackRow.index[0]
    prevEntrys = frame.loc[(frame["user"] == trackRow["user"][trackIDx]) & (frame.index < trackIDx)]
    return len(prevEntrys.index)


async def PopularityRanking(track: str, useFollowers: bool = False) -> float:
    try:
        trackInfo = await GetFullInfo(track)
        val = (
            (0.75 * trackInfo["track"]["popularity"]) + (0.25 * trackInfo["artist"]["popularity"])
            if not useFollowers
            else trackInfo["artist"]["followers"]["total"]
        )
    except:
        val = -1.0
    return val


def AvgPopularityAtRow(frame: pd.DataFrame, row: int, useFollowers: bool = False) -> float:
    trackRow = frame.iloc[row]
    trackIdx = trackRow.name
    prevEntrys = frame.loc[frame.index <= trackIdx]
    return round(
        sum(prevEntrys["popularity" if not useFollowers else "followers"]) / len(prevEntrys.index),
        2,
    )


async def PrepDataFrame() -> pd.DataFrame:
    df = pd.read_csv(USER_DATA_FILE)

    df["popularity"] = [await PopularityRanking(x) for x in df["track"]]
    df["followers"] = [await PopularityRanking(x, True) for x in df["track"]]
    df["userCount"] = [UserTrackNum(df, x) for x in df["track"]]
    df["average"] = [AvgPopularityAtRow(df, x) for x in df.index]
    df["followers_average"] = [AvgPopularityAtRow(df, x, True) for x in df.index]
    df.to_csv(TEMP_USER_DATA_FILE, sep=",", encoding="utf-8", index=False, header=True)

    return df


def GetUniqueRatio(data: pd.DataFrame) -> float:
    return len(set(data)) / len(data) if len(data) > 0 else 1.0


async def PrepUserData(df: pd.DataFrame) -> pd.DataFrame:
    users = pd.DataFrame({"names": list(set(df["user"]))})
    users["artists"] = [df[df["user"] == user]["artist"] for user in users["names"]]
    users["count"] = [len(df[df["user"] == user]) for user in users["names"]]
    users["genres"] = [
        [
            genre
            for row in df[df["user"] == user].itertuples(index=False)
            for genre in (await GetFullInfo(row.track))["artist"]["genres"]
        ]
        for user in users["names"]
    ]
    users["genre_ratio"] = users["genres"].apply(GetUniqueRatio)
    users["artist_ratio"] = users["artists"].apply(GetUniqueRatio)
    users["average_popularity"] = [
        sum(df[df["user"] == user]["popularity"]) for user in users["name"]
    ]
    users["overall_score"] = [
        users[users["name"] == name]["artist_ratio"] * users[users["name"] == name]["genre_ratio"]
        - (abs(50 - users[users["name"] == name]["average_popularity"]) * 0.01)
        for name in users["names"]
    ]
    return users


async def Graphs(message: Message) -> list[Path]:
    full = await PrepDataFrame()
    valid = full.loc[full["result"] == Status.Added]
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
            x="name",
            y="overall_score",
            color="name",
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
    }
    (USER_DATA_FILE.parent / "graphs").mkdir(exist_ok=True)
    made: list[Path] = []
    figs: list = []
    for graph, func in graphs.items():
        if graph in message.content or " all" in message.content:
            figs.append(func())
            figs[-1].update_layout(xaxis={"categoryorder": "total ascending"})
            print(f"generated {graph}")
            made.append(USER_DATA_FILE.parent / "graphs" / f"{graph}.png")
    pio.write_images(fig=figs, file=made, width=960, height=540, scale=2)
    return made
