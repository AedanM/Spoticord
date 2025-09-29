# Spoticord

![icon.png](icon.png)

## Introduction

**Spoticord** is a Discord bot that integrates with Spotify to automate playlist management

## Features

- **Banned Artist Filtering:** Prevents songs by blacklisted artists from being added.
- **User Data Logging:** Tracks who adds which songs for accountability and fun stats.
- **Statistics Reports:** Generates reports on user activity and playlist trends.
- **Automatic Daily Pokes:** Reminds users to add new music or interact with the bot.
- **Special Event Handling:** Supports custom events and seasonal features.
- **Self-Update & Refresh:** Can update itself and refresh its state without manual intervention.
- **Dad Jokes:** Always required

## Usage

Run the bot using the uv package manager for best results

```sh
    uv run .\src\Spoticord.py
```

Invite the bot to your Discord server and use the available commands to manage your Spotify playlists. The bot will automatically monitor activity and enforce rules as configured.

## Configuration

Edit the configuration files in the `Configs/` directory to set up your Spotify and Discord API credentials, banned artists, and other preferences.
