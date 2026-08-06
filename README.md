# Torrent Media Stack 🚀

A portable, single-command media automation & torrenting stack bundled with a unified CLI. Supports **Movies**, **TV Shows**, **Anime**, and **PC Games** with safe, curated indexers vetted by the r/Piracy Megathread.

---

## 📋 Table of Contents
- [Features](#features)
- [Safe Sources vs. Unsafe Sources](#-safe-sources-vs-unsafe-sources)
- [Quick Start](#-quick-start)
- [Web UI Guide (Movies, TV & Anime)](#-web-ui-guide-movies-tv--anime)
- [Terminal CLI Request Guide](#-terminal-cli-request-guide)
  - [Requesting TV Shows & Anime](#1-requesting-tv-shows--anime)
  - [Requesting Movies](#2-requesting-movies)
  - [Searching & Downloading Games](#3-searching--downloading-pc-games)
- [Services & Web UI Access](#-services--web-ui-access)
- [Stack Management Commands](#-stack-management-commands)

---

## ✨ Features

- **Safe Sources**: Pre-configured with r/Piracy-approved safe indexers (**1337x**, **Nyaa.si**, **TorrentGalaxy**, **EZTV**, **YTS**, **LimeTorrents**, **RuTracker**). Unsafe sites like The Pirate Bay and IGG-Games are strictly excluded.
- **Full Media Coverage**: 
  - **Movies & TV Shows**: Fully automated via Radarr, Sonarr, and Jellyseerr.
  - **Anime**: Native tracking & release handling via Sonarr + Nyaa.
  - **Games**: Dedicated CLI search & downloader querying 1337x (FitGirl/DODI repacks) and RuTracker.
- **User-Facing Request UI**: **Jellyseerr** provides a slick, Netflix-style web UI for requesting Movies, TV shows, and Anime.
- **Unified CLI Tool**: Single executable command to set up, start, stop, request media, and interactively search/download PC games directly from your terminal.
- **Custom Destination**: Specify any destination folder (`./media-stack init --dest /path/to/media`) for storing downloaded files under organized `/movies`, `/tv`, `/anime`, `/games`, and `/torrents` subdirectories.

---

## 🛡️ Safe Sources vs. Unsafe Sources

### Included Safe Indexers (Pre-Configured in Prowlarr)
| Indexer | Content Type | Notes |
| :--- | :--- | :--- |
| **1337x** | Movies, TV, Games | Super hub; primary source for verified FitGirl/DODI repacks and movie/TV releases. |
| **Nyaa.si** | Anime & Asian Media | The gold standard tracker for subbed/dubbed anime. |
| **TorrentGalaxy** | Movies & TV | High quality 1080p/4K web rips and fast TV episode uploads. |
| **EZTV** | TV Shows | Dedicated TV series indexer. |
| **YTS** | Movies | Optimized, small file-size movie encodes. |
| **LimeTorrents** | General Media | Verified public tracker fallback. |
| **RuTracker** | Games & Media | World's premier tracker for PC game ISOs, rare audio, software, and media. |

### Excluded Unsafe Sources ❌
* ❌ **The Pirate Bay (TPB)**: Excluded due to unmoderated uploaders, fake verified badges, and high risk of malware/crypto-miners in `.exe`/`.iso` downloads.
* ❌ **IGG-Games**: Excluded due to history of malware bundling, ad-redirect abuses, and DRM watermarking.

---

## ⚡ Quick Start

### 1. Initialize Destination Folder
Specify where you want downloaded media to be stored:
```bash
./media-stack init --dest ~/Downloads/Media
```
*Creates `/movies`, `/tv`, `/anime`, `/games`, and `/torrents` under the specified folder and configures `.env`.*

### 2. Start Services & Provision Stack
Spins up Docker containers and auto-configures API keys, download client links, and Prowlarr indexers automatically:
```bash
./media-stack up
```

### 3. Check Stack Status
```bash
./media-stack status
```

---

## 🌐 Web UI Guide (Movies, TV & Anime)

For browsing and requesting Movies, TV Shows, and Anime visually:

1. Open **Jellyseerr** at **`http://localhost:5055`** in your browser.
2. Sign in or complete the quick first-time setup screen (pairs with Jellyfin/Plex or local admin account).
3. **Search for content**: Type any Movie, TV show, or Anime title in the search bar.
4. **Click "Request"**: Select seasons/episodes or quality profile and click **Request**.
5. **Automation Pipeline**:
   * Jellyseerr sends the request to **Sonarr** (for TV/Anime) or **Radarr** (for Movies).
   * Sonarr/Radarr queries **Prowlarr** to fetch magnet links from safe indexers (1337x, Nyaa, TGx, etc.).
   * Downloads are automatically sent to **qBittorrent** (`http://localhost:8080`) and organized into your destination folder!

---

## 💻 Terminal CLI Request Guide

You can also request content directly from your command line without opening a browser.

### 1. Requesting TV Shows & Anime
```bash
# Standard TV Series:
./media-stack request "Breaking Bad"

# Anime Series (Subbed by default, or explicitly with --sub):
./media-stack request "Chainsaw Man" --type anime
./media-stack request "Chainsaw Man" --type anime --sub

# Anime Series with English Dub / Dual Audio preference:
./media-stack request "Chainsaw Man" --type anime --dub
```
* **What it does**: Connects to Sonarr/TVDB, monitors the series, and instructs Sonarr to auto-grab episodes from safe indexers. Subbed (Japanese audio + English subtitles) is the default release format for anime indexers like Nyaa. The `--dub` flag configures Sonarr to automatically prefer English Dub / Dual Audio releases (`Dual Audio`, `Dub`, `English Dub`).

---

### 2. Requesting Movies
```bash
./media-stack request-movie "Inception"
```
* **What it does**: Connects to Radarr/TMDB, adds the movie to your monitored library, and automatically downloads the best available release.

---

### 3. Searching & Downloading PC Games
```bash
./media-stack request-game "Cyberpunk 2077"
```

#### How Game Selection Works:
When you search for a game, the CLI queries Prowlarr indexers (**1337x** for FitGirl/DODI repacks & **RuTracker** for game ISOs), filters out results over 100 GB, sorts by seeder count, and presents an **interactive selection menu**:

```text
Searching safe indexers for game release 'Cyberpunk 2077'...

Found 5 game releases (Top 5):
  [1] Cyberpunk 2077 (v2.12 + All DLCs) [FitGirl Repack]
      Size: 56.40 GB | Seeders: 342 | Source: 1337x

  [2] Cyberpunk 2077 Phantom Liberty-DODI Repack
      Size: 62.10 GB | Seeders: 180 | Source: 1337x

  [3] Cyberpunk.2077.v2.12-RuTracker
      Size: 84.00 GB | Seeders: 95  | Source: RuTracker

Select release to download [1-5] (default 1): 1

Selected Game Release:
Title: Cyberpunk 2077 (v2.12 + All DLCs) [FitGirl Repack]
Size: 56.40 GB
Seeders: 342
Source: 1337x
✓ Download queued successfully in qBittorrent under category 'games'!
```

### 4. Interactive Search (All Media Types)
You can interactively search safe indexers for any release (Anime, TV, Movies, Games) directly in your terminal:
```bash
./media-stack search "Chainsaw Man" --category anime
./media-stack request "Chainsaw Man" --type anime -i
```

#### Screen Output Format:
When searching, the CLI parses and displays release options with clean **Type** (`[SUB]`, `[DUB]`, `[DUAL AUDIO]`), **Quality** (`1080p`, `4K`, `BluRay`, `HEVC`), **Size**, **Seeders**, and **Source**:

```text
Found 5 releases (Top 5):
──────────────────────────────────────────────────────────────────────
  [1] Chainsaw.Man.S01.1080p.Dual.Audio.BD.x265-Judas
      Type: [DUAL AUDIO]   | Quality: 1080p | BluRay | x265/HEVC
      Size: 4.20 GB     | Seeders: 215   | Source: Nyaa.si

  [2] [SubsPlease] Chainsaw Man - 01-12 (1080p) [AAC]
      Type: [SUB]          | Quality: 1080p
      Size: 3.80 GB     | Seeders: 180   | Source: Nyaa.si

  [3] Chainsaw Man S01 1080p Dual Audio BDRip x264
      Type: [DUAL AUDIO]   | Quality: 1080p | BluRay | x264
      Size: 12.40 GB    | Seeders: 94    | Source: 1337x

Select release to download [1-5] (default 1): 1
```

#### Non-Interactive / Auto-Confirm Flag (`-y` / `--yes`):
To automatically select the top-seeded release without asking for confirmation:
```bash
./media-stack search "Chainsaw Man" -y
```

#### Limit Size Flag (`-l` / `--limit`):
To set a custom maximum file size limit in GB (default: 100 GB):
```bash
./media-stack search "GTA V" --category games --limit 75
```

---

## 🔗 Services & Web UI Access

| Service | Purpose | URL | Default Credentials |
| :--- | :--- | :--- | :--- |
| 🍿 **Jellyseerr** | Netflix-style Request UI | [http://localhost:5055](http://localhost:5055) | Set on first boot |
| 📺 **Sonarr** | TV & Anime Automation | [http://localhost:8989](http://localhost:8989) | Pre-configured via CLI |
| 🎬 **Radarr** | Movie Automation | [http://localhost:7878](http://localhost:7878) | Pre-configured via CLI |
| 🔍 **Prowlarr** | Indexer Manager | [http://localhost:9696](http://localhost:9696) | Pre-configured via CLI |
| ⚡ **qBittorrent** | Downloader WebUI | [http://localhost:8080](http://localhost:8080) | `admin` / `adminadmin` |

---

## 🛠️ Stack Management Commands

```bash
./media-stack init --dest /path  # Set destination folder & create structure
./media-stack up                 # Launch Docker containers & auto-provision indexers
./media-stack down               # Stop all stack services
./media-stack status             # Display health status & access URLs
./media-stack logs               # View combined container output logs
```

---

## 🙏 Credits & Acknowledgments

- **[r/Piracy Megathread](https://www.reddit.com/r/Piracy/wiki/megathread)**: Huge thanks to the r/Piracy community and Megathread maintainers for their extensive security research, safety guidelines, and curated indexer recommendations.
- **[Servarr Team](https://servarr.com)**: Developers of Sonarr, Radarr, and Prowlarr.
- **[Jellyseerr / Overseerr](https://github.com/FallenBagel/jellyseerr)**: For the fantastic media request UI.

