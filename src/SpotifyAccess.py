import random

import spotipy
from Defines import CONFIG, SPOTIFY_CLIENT, GetUserData, Status


def GetAllTracks(playlistId):
    results = SPOTIFY_CLIENT.playlist_tracks(playlistId)
    tracks = results["items"]
    while results["next"]:
        results = SPOTIFY_CLIENT.next(results)
        tracks.extend(results["items"])
    return tracks


async def IsARepeat(trackId: str) -> bool:
    matches = [
        x for x in await GetUserData() if x.TrackId == trackId and x.EntryStatus.WasSuccessful
    ]
    return len(matches) > 0


def IsInRegion(regions: list[str]) -> bool:
    # todo re-implement region codes
    # if regions and "GB" not in regions:
    #
    return True


async def AddToPlaylist(trackId: str, playlistId: str, isTesting: bool) -> tuple[Status, tuple]:
    result = Status.Default

    if await IsARepeat(trackId):
        result = Status.Repeat

    addChance, title, artist, uri, regions = GetTrackInformation(trackId)

    if result == Status.Default and not IsInRegion(regions):
        result = Status.WrongMarket
    if result == Status.Default and random.random() < addChance:
        result = Status.BadVibes

    if result == Status.Default:
        if exception := AddTrack(trackId, playlistId, isTesting):
            print(exception)
            result = Status.Failed
        else:
            result = Status.Added

    return (result, (trackId, title, artist, uri))


def AddTrack(trackId, playlistId, isTesting) -> spotipy.exceptions.SpotifyException | None:
    try:
        if not isTesting:
            SPOTIFY_CLIENT.playlist_add_items(playlistId, [trackId])
    except spotipy.exceptions.SpotifyException as e:
        return e


def ForceTrack(trackId, playlistId) -> tuple[Status, tuple]:
    _addChance, title, artist, uri, _regions = GetTrackInformation(trackId)

    if _exception := AddTrack(trackId, playlistId, False):
        title = "ERROR"
        artist = "ERROR"

    return (Status.ForceAdd, (trackId, title, artist, uri))


def GetTrackInformation(trackId) -> tuple:
    r = SPOTIFY_CLIENT.track(trackId)
    vibe = 0.0
    for artist in r["artists"]:
        v = CONFIG["Vibes"].get(artist["id"], 0.0)
        vibe = max(v, vibe)
    return (
        vibe,
        r["name"],
        r["artists"][0]["name"],
        r["uri"],
        r["available_markets"],
    )


def GetFullInfo(trackId: str, skipArtist: bool = False) -> dict[str, dict]:
    r = SPOTIFY_CLIENT.track(trackId)
    topArtist = SPOTIFY_CLIENT.artist(r["artists"][0]["id"]) if not skipArtist else {}
    return {"track": r, "artist": topArtist}
