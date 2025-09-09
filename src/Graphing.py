from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.express as px
from discord import Message

from Defines import TEMP_USER_DATA_FILE, USER_DATA_FILE, Status
from SpotifyAccess import GetFullInfo

GRAPHS = {"popularityTrend", "popularity", "progress", "users"}


def UserTrackNum(frame: pd.DataFrame, track: str) -> int:
    trackRow = frame.loc[frame["track"] == track]
    trackIDx = trackRow.index[0]
    prevEntrys = frame.loc[(frame["user"] == trackRow["user"][trackIDx]) & (frame.index < trackIDx)]
    return len(prevEntrys.index)


async def PopularityRanking(track: str) -> float:
    trackInfo = await GetFullInfo(track)
    return (0.75 * trackInfo["track"]["popularity"]) + (0.25 * trackInfo["artist"]["popularity"])


def PrepDataFrame() -> pd.DataFrame:
    df = pd.read_csv(USER_DATA_FILE)

    df["popularity"] = [PopularityRanking(x) for x in df["track"]]
    df["userCount"] = [UserTrackNum(df, x) for x in df["track"]]
    df.to_csv(TEMP_USER_DATA_FILE, sep=",", encoding="utf-8", index=False, header=True)

    return df


def Graphs(message: Message) -> list[Path]:
    full = PrepDataFrame()
    valid = full.loc[full["result"] == Status.Added]
    graphs: dict[str, Callable] = {
        "popularityTrend": lambda: px.scatter(
            valid,
            x=valid.index,
            y="popularity",
            color="user",
            trendline="lowess",
        ),
        "popularity": lambda: px.scatter(
            valid,
            x="count",
            y="popularity",
            color="user",
            trendline="lowess",
        ),
        "progress": lambda: px.scatter(
            valid,
            x="time",
            y=valid.index,
            color="user",
        ),
        "users": lambda: px.pie(
            valid,
            values="tracks",
            names="user",
        ),
    }
    (USER_DATA_FILE.parent / "graphs").mkdir(exist_ok=True)
    made: list[Path] = []
    for graph, func in graphs.items():
        if graph in message.Content or " all" in message.content:
            fig = func()
            dst = USER_DATA_FILE.parent / "graphs" / f"{graph}.png"
            fig.write_image(dst)
            made.append(dst)
    return made
