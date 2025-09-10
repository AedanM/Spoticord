import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
from discord import Message

from Defines import CONFIG, TEMP_USER_DATA_FILE, USER_DATA_FILE, Status
from SpotifyAccess import GetFullInfo

GRAPHS = {"popularityTrend", "popularityAverage", "popularity", "progress", "users", "unique"}


def UserTrackNum(frame: pd.DataFrame, track: str) -> int:
    trackRow = frame.loc[frame["track"] == track]
    trackIDx = trackRow.index[0]
    prevEntrys = frame.loc[(frame["user"] == trackRow["user"][trackIDx]) & (frame.index < trackIDx)]
    return len(prevEntrys.index)


async def PopularityRanking(track: str) -> float:
    try:
        trackInfo = await GetFullInfo(track)
        val = (0.75 * trackInfo["track"]["popularity"]) + (0.25 * trackInfo["artist"]["popularity"])
    except:
        val = -1.0
    return val


def AvgPopularityAtRow(frame: pd.DataFrame, row: int) -> float:
    trackRow = frame.iloc[row]
    trackIdx = trackRow.name
    prevEntrys = frame.loc[frame.index <= trackIdx]
    return round(sum(prevEntrys["popularity"]) / len(prevEntrys.index), 2)


async def PrepDataFrame() -> pd.DataFrame:
    df = pd.read_csv(USER_DATA_FILE)

    df["popularity"] = [await PopularityRanking(x) for x in df["track"]]
    df["userCount"] = [UserTrackNum(df, x) for x in df["track"]]
    df["average"] = [AvgPopularityAtRow(df, x) for x in df.index]
    df.to_csv(TEMP_USER_DATA_FILE, sep=",", encoding="utf-8", index=False, header=True)

    return df


async def Graphs(message: Message) -> list[Path]:
    full = await PrepDataFrame()
    valid = full.loc[full["result"] == Status.Added]
    users = set(valid["user"])
    valid.reset_index(drop=True)
    graphs: dict[str, Callable] = {
        "popularityTrend": lambda: px.scatter(
            valid,
            x=valid.index,
            y="popularity",
            color="user",
            trendline="lowess",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "popularity": lambda: px.scatter(
            valid,
            x="userCount",
            y="popularity",
            color="user",
            trendline="lowess",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "popularityAverage": lambda: px.scatter(
            valid,
            x=valid.index,
            y="average",
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
            pd.DataFrame({"user": valid["user"]}).value_counts().reset_index(name="count"),
            names="user",
            values="count",
            color="user",
            color_discrete_map=CONFIG["UserColors"],
        ),
        "unique": lambda: px.bar(
            pd.DataFrame(
                {
                    "user": list(users),
                    "uniqueness": [
                        valid[valid["user"] == user]["artist"].nunique()
                        / valid[valid["user"] == user].shape[0]
                        for user in users
                    ],
                },
            ),
            x="user",
            y="uniqueness",
            color="user",
            color_discrete_map=CONFIG["UserColors"],
        ),
    }
    (USER_DATA_FILE.parent / "graphs").mkdir(exist_ok=True)
    made: list[Path] = []
    figs: list = []
    for graph, func in graphs.items():
        if re.search(rf"\s{graph}\s?$", message.content) or " all" in message.content:
            figs.append(func())
            made.append(USER_DATA_FILE.parent / "graphs" / f"{graph}.png")
    pio.write_images(fig=figs, file=made, width=1920, height=1080, scale=2)
    return made
