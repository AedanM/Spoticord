import sys
from enum import StrEnum
from pathlib import Path

import discord
import spotipy
from discord.ext import commands
from spotipy.oauth2 import SpotifyOAuth
from yaml import Loader, load

CONFIG_PATH: Path = Path("data/conf.yml" if len(sys.argv) < 2 else sys.argv[1])
USER_DATA_FILE: Path = Path("data/user_data.csv")
UNAME_STAND_IN = "UNAME_STANDIN"

CONFIG: dict = load(CONFIG_PATH.read_text(encoding="utf-8"), Loader)

DISCORD_INTENTS: discord.Intents = discord.Intents.default()
DISCORD_INTENTS.message_content = True
DISCORD_CLIENT: discord.Client = commands.Bot(command_prefix="!*", intents=DISCORD_INTENTS)

SPOTIFY_SCOPE = "playlist-modify-public"
SPOTIFY_CLIENT = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope=SPOTIFY_SCOPE,
        client_id=CONFIG["SpotifyID"],
        client_secret=CONFIG["SpotifySecret"],
        redirect_uri="http://127.0.0.1:3000",
    )
)


class RequestResults(StrEnum):
    Added = "Added"
    Failed = "Failed"
    Repeat = "Repeat"
    BadVibes = "Failed Vibes"
    RegexFail = "Failed Regex"
    WrongMarket = "Wrong Market"
