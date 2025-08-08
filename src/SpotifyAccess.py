import random

import polars as pl
import spotipy
from DataLogging import CURRENT_USER_DATA
from Defines import CONFIG, SPOTIFY_CLIENT, UNAME_STAND_IN, RequestResults


def AddSongToPlaylist(
    trackId: str, playlistId: str, isTesting: bool
) -> tuple[RequestResults, str, tuple]:
    trackInfo = (trackId, "", "", "")
    if trackId in CURRENT_USER_DATA["track"]:

        for r in CURRENT_USER_DATA.rows_by_key(key="track", named=True)[trackId]:
            if r["result"] == str(RequestResults.Added):
                return (
                    RequestResults.Repeat,
                    (
                        "Already in the playlist, @everyone mock them"
                        if not isTesting
                        else "Try again bucko, already added"
                    ),
                    trackInfo,
                )
    try:
        addChance, title, artist, uri, regions = ArtistVibeCheck(trackId)
        trackInfo = (trackId, title, artist, uri)
        if "GB" not in regions:
            return (RequestResults.WrongMarket, "Track not available in the UK, sorry", trackInfo)
        if random.random() < addChance:
            return (
                RequestResults.BadVibes,
                f"@{UNAME_STAND_IN} You failed the Pedo Check. Reconsider your choices",
                trackInfo,
            )
        if not isTesting:
            SPOTIFY_CLIENT.playlist_add_items(playlistId, [trackId])
        return (RequestResults.Added, "", trackInfo)
    except spotipy.exceptions.SpotifyException as e:
        return (
            RequestResults.Failed,
            f"You broke spotify with that id ({trackId}). Thanks numbnuts",
            (trackId, e, "", ""),
        )


def ArtistVibeCheck(trackId) -> tuple:
    r = SPOTIFY_CLIENT.track(trackId)
    vibe = 0.0
    mainArtist = r["artists"][0]["name"]
    title = r["name"]
    uri = r["uri"]
    regions = r["available_markets"]
    for artist in r["artists"]:
        v = CONFIG["Vibes"].get(artist["id"], 0.0)
        vibe = max(v, vibe)
    return (vibe, title, mainArtist, uri, regions)
