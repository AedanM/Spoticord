import random

import requests
from Defines import CONFIG, SPOTIFY_CLIENT, RequestResults


def AddSongToPlaylist(trackId: str, playlistId: str) -> tuple[RequestResults, str, tuple]:
    addChance, title, artist, uri = ArtistVibeCheck(trackId)
    trackInfo = (trackId, title, artist, uri)
    if random.random() < addChance:
        return (
            RequestResults.BadVibes,
            "Failed the Pedo Check. Reconsider your choices",
            trackInfo,
        )
    SPOTIFY_CLIENT.playlist_add_items(playlistId, [trackId])
    return (RequestResults.Added, "", trackInfo)


def ArtistVibeCheck(trackId) -> tuple:
    r = SPOTIFY_CLIENT.track(trackId)
    vibe = 0.0
    mainArtist = r["artists"][0]["name"]
    title = r["name"]
    uri = r["uri"]
    for artist in r["artists"]:
        v = CONFIG["Vibes"].get(artist["id"], 0.0)
        vibe = max(v, vibe)
    return (vibe, title, mainArtist, uri)
