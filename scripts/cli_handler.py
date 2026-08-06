#!/usr/bin/env python3
import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))


def load_env():
    env_vars = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


ENV = load_env()

SONARR_URL = os.environ.get("SONARR_URL", ENV.get("SONARR_URL", "http://localhost:8989/api/v3"))
RADARR_URL = os.environ.get("RADARR_URL", ENV.get("RADARR_URL", "http://localhost:7878/api/v3"))
PROWLARR_URL = os.environ.get("PROWLARR_URL", ENV.get("PROWLARR_URL", "http://localhost:9696/api/v1"))
QBIT_URL = os.environ.get("QBITTORRENT_URL", ENV.get("QBITTORRENT_URL", "http://localhost:8080"))

SONARR_API_KEY = os.environ.get("SONARR_API_KEY", ENV.get("SONARR_API_KEY"))
RADARR_API_KEY = os.environ.get("RADARR_API_KEY", ENV.get("RADARR_API_KEY"))
PROWLARR_API_KEY = os.environ.get("PROWLARR_API_KEY", ENV.get("PROWLARR_API_KEY"))
QBIT_PASSWORD = os.environ.get("QBITTORRENT_PASSWORD", ENV.get("QBITTORRENT_PASSWORD", "adminadmin"))


def make_request(url, method="GET", headers=None, data=None, timeout=15):
    request_headers = dict(headers or {})
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} for {url}: {e.read().decode('utf-8')}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error connecting to {url}: {e}", file=sys.stderr)
        raise


def add_to_qbittorrent(magnet_or_url, category="tv", save_path=None):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    print("Connecting to qBittorrent WebUI...")
    login_data = urllib.parse.urlencode({"username": "admin", "password": QBIT_PASSWORD}).encode("utf-8")
    try:
        opener.open(urllib.request.Request(f"{QBIT_URL}/api/v2/auth/login", data=login_data)).read()
    except Exception as e:
        print(f"qBittorrent login failed: {e}", file=sys.stderr)
        return False

    params = {"urls": magnet_or_url, "category": category}
    if save_path:
        params["savepath"] = save_path

    add_data = urllib.parse.urlencode(params).encode("utf-8")
    try:
        opener.open(urllib.request.Request(f"{QBIT_URL}/api/v2/torrents/add", data=add_data)).read()
        print(f"✓ Download queued successfully in qBittorrent under category '{category}'!")
        return True
    except Exception as e:
        print(f"Failed to queue torrent in qBittorrent: {e}", file=sys.stderr)
        return False


def ensure_dub_tag_and_profile(headers):
    try:
        tags = make_request(f"{SONARR_URL}/tag", headers=headers)
        dub_tag = next((t for t in tags if t.get("label") == "dub"), None)
        if not dub_tag:
            dub_tag = make_request(f"{SONARR_URL}/tag", method="POST", headers=headers, data={"label": "dub"})
        tag_id = dub_tag.get("id")

        profiles = make_request(f"{SONARR_URL}/releaseprofile", headers=headers)
        dub_profile = next((p for p in profiles if p.get("name") == "Dub Preferred"), None)
        if not dub_profile:
            new_profile = {
                "name": "Dub Preferred",
                "enabled": True,
                "indexerId": 0,
                "tags": [tag_id] if tag_id else [],
                "mustContain": "",
                "mustNotContain": "",
                "preferred": [
                    {"key": "Dual Audio", "value": 100},
                    {"key": "Dual-Audio", "value": 100},
                    {"key": "Dub", "value": 100},
                    {"key": "English Dub", "value": 100},
                ],
            }
            make_request(f"{SONARR_URL}/releaseprofile", method="POST", headers=headers, data=new_profile)
        elif tag_id and tag_id not in dub_profile.get("tags", []):
            dub_profile["tags"].append(tag_id)
            make_request(f"{SONARR_URL}/releaseprofile/{dub_profile['id']}", method="PUT", headers=headers, data=dub_profile)

        return tag_id
    except Exception as e:
        print(f"Warning: Could not configure dub profile in Sonarr: {e}", file=sys.stderr)
        return None


def request_tv(query, series_type="anime", quality_id=4, dub=False):
    if not SONARR_API_KEY:
        print("Error: SONARR_API_KEY is not set. Run `./media-stack up` first.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Api-Key": SONARR_API_KEY}
    print(f"Searching for TV series '{query}' in Sonarr...")
    lookup = make_request(f"{SONARR_URL}/series/lookup?term={urllib.parse.quote(query)}", headers=headers)
    if not lookup:
        print("No matching series found.", file=sys.stderr)
        return

    series = lookup[0]
    series["rootFolderPath"] = "/data/tv" if series_type != "anime" else "/data/anime"
    series["qualityProfileId"] = quality_id
    series["seriesType"] = series_type
    series["monitored"] = True
    series["addOptions"] = {"searchForMissingEpisodes": True, "monitor": "all"}

    if dub:
        tag_id = ensure_dub_tag_and_profile(headers)
        if tag_id:
            series["tags"] = [tag_id]
            print("✓ English Dub / Dual Audio release preference applied.")

    print(f"Adding '{series.get('title')}' ({series.get('year')}) to Sonarr...")
    added = make_request(f"{SONARR_URL}/series", method="POST", headers=headers, data=series)
    print(f"✓ Added series: {added.get('title')}. Sonarr will manage & download episodes via safe indexers.")



def request_movie(query, quality_id=1):
    if not RADARR_API_KEY:
        print("Error: RADARR_API_KEY is not set. Run `./media-stack up` first.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Api-Key": RADARR_API_KEY}
    print(f"Searching for Movie '{query}' in Radarr...")
    lookup = make_request(f"{RADARR_URL}/movie/lookup?term={urllib.parse.quote(query)}", headers=headers)
    if not lookup:
        print("No matching movies found.", file=sys.stderr)
        return

    movie = lookup[0]
    movie["rootFolderPath"] = "/data/movies"
    movie["qualityProfileId"] = quality_id
    movie["monitored"] = True
    movie["addOptions"] = {"searchForMovie": True}

    print(f"Adding '{movie.get('title')}' ({movie.get('year')}) to Radarr...")
    added = make_request(f"{RADARR_URL}/movie", method="POST", headers=headers, data=movie)
    print(f"✓ Added movie: {added.get('title')}. Radarr will monitor and download it automatically.")


def parse_release_info(title):
    t_lower = title.lower()

    # 1. Audio / Sub Type
    audio_type = "SUB"
    if any(k in t_lower for k in ["dual audio", "dual-audio", "multi-audio", "multi audio", "multi-lang", "multi lang"]):
        audio_type = "DUAL AUDIO"
    elif any(k in t_lower for k in ["dubbed", " english dub", " eng dub", "[dub]", "(dub)", " dub "]):
        audio_type = "DUB"
    elif any(k in t_lower for k in ["subbed", " english sub", " eng sub", "[sub]", "(sub)", " sub ", "subsplease", "erai-raws"]):
        audio_type = "SUB"

    # 2. Resolution
    if "2160p" in t_lower or "4k" in t_lower or "uhd" in t_lower:
        res = "4K/2160p"
    elif "1080p" in t_lower:
        res = "1080p"
    elif "720p" in t_lower:
        res = "720p"
    elif "480p" in t_lower:
        res = "480p"
    else:
        res = "HD"

    # 3. Source
    source = ""
    if any(k in t_lower for k in ["bluray", "blu-ray", "bdrip", "brrip", "bd"]):
        source = "BluRay"
    elif any(k in t_lower for k in ["web-dl", "webrip", "web"]):
        source = "WEB-DL"
    elif "hdtv" in t_lower:
        source = "HDTV"
    elif "repack" in t_lower:
        source = "Repack"

    # 4. Codec
    codec = ""
    if any(k in t_lower for k in ["hevc", "x265", "h265", "h.265"]):
        codec = "x265/HEVC"
    elif any(k in t_lower for k in ["x264", "h264", "h.264"]):
        codec = "x264"
    elif "av1" in t_lower:
        codec = "AV1"

    quality_parts = [p for p in [res, source, codec] if p]
    quality_str = " | ".join(quality_parts)

    return {
        "audio": audio_type,
        "quality": quality_str
    }


def display_releases(results, top_n=5, auto_confirm=False, limit_gb=100.0):
    if not results:
        print("No releases found.", file=sys.stderr)
        return None

    filtered = []
    for item in results:
        size_gb = item.get("size", 0) / (1024 ** 3)
        if size_gb > limit_gb:
            continue
        size_str = f"{size_gb:.2f} GB" if size_gb >= 1.0 else f"{item.get('size', 0) / (1024 ** 2):.1f} MB"
        parsed = parse_release_info(item.get("title", ""))
        filtered.append({
            "title": item.get("title"),
            "size_str": size_str,
            "seeders": item.get("seeders", 0),
            "indexer": item.get("indexer"),
            "audio": parsed["audio"],
            "quality": parsed["quality"],
            "guid": item.get("guid") or item.get("downloadUrl"),
        })

    if not filtered:
        print(f"No releases found under size limit ({limit_gb:.0f} GB).", file=sys.stderr)
        return None

    filtered.sort(key=lambda x: x["seeders"], reverse=True)
    show_count = min(len(filtered), top_n)

    print(f"\nFound {len(filtered)} releases (Top {show_count}):")
    print("─" * 70)
    for idx, item in enumerate(filtered[:show_count]):
        audio_badge = f"[{item['audio']}]"
        print(f"  [{idx + 1}] {item['title']}")
        print(f"      Type: {audio_badge:<14} | Quality: {item['quality']}")
        print(f"      Size: {item['size_str']:<10} | Seeders: {item['seeders']:<5} | Source: {item['indexer']}\n")

    choice = 0
    if not auto_confirm and show_count > 1:
        try:
            choice_str = input(f"Select release to download [1-{show_count}] (default 1): ").strip()
            choice = int(choice_str) - 1 if choice_str and choice_str.isdigit() and 1 <= int(choice_str) <= show_count else 0
        except Exception:
            choice = 0

    selected = filtered[choice]
    print(f"\nSelected Release:")
    print(f"Title: {selected['title']}\nType: [{selected['audio']}] | Quality: {selected['quality']}\nSize: {selected['size_str']} | Seeders: {selected['seeders']} | Source: {selected['indexer']}")
    return selected


def search_interactive(query, category="tv", limit_gb=100.0, auto_confirm=False):
    if not PROWLARR_API_KEY:
        print("Error: PROWLARR_API_KEY is not set. Run `./media-stack up` first.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Api-Key": PROWLARR_API_KEY}
    print(f"Searching indexers for '{query}'...")
    results = make_request(f"{PROWLARR_URL}/search?query={urllib.parse.quote(query)}", headers=headers)

    selected = display_releases(results, auto_confirm=auto_confirm, limit_gb=limit_gb)
    if selected:
        save_dir = f"/data/{category}"
        add_to_qbittorrent(selected["guid"], category=category, save_path=save_dir)


def request_tv(query, series_type="anime", quality_id=4, dub=False, interactive=False):
    if interactive:
        search_query = f"{query} Dub" if dub else query
        search_interactive(search_query, category="anime" if series_type == "anime" else "tv")
        return

    if not SONARR_API_KEY:
        print("Error: SONARR_API_KEY is not set. Run `./media-stack up` first.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Api-Key": SONARR_API_KEY}
    print(f"Searching for TV series '{query}' in Sonarr...")
    lookup = make_request(f"{SONARR_URL}/series/lookup?term={urllib.parse.quote(query)}", headers=headers)
    if not lookup:
        print("No matching series found.", file=sys.stderr)
        return

    series = lookup[0]
    series["rootFolderPath"] = "/data/tv" if series_type != "anime" else "/data/anime"
    series["qualityProfileId"] = quality_id
    series["seriesType"] = series_type
    series["monitored"] = True
    series["addOptions"] = {"searchForMissingEpisodes": True, "monitor": "all"}

    if dub:
        tag_id = ensure_dub_tag_and_profile(headers)
        if tag_id:
            series["tags"] = [tag_id]
            print("✓ English Dub / Dual Audio release preference applied.")

    print(f"Adding '{series.get('title')}' ({series.get('year')}) to Sonarr...")
    added = make_request(f"{SONARR_URL}/series", method="POST", headers=headers, data=series)
    print(f"✓ Added series: {added.get('title')}. Sonarr will manage & download episodes via safe indexers.")


def request_movie(query, quality_id=1, interactive=False):
    if interactive:
        search_interactive(query, category="movies")
        return

    if not RADARR_API_KEY:
        print("Error: RADARR_API_KEY is not set. Run `./media-stack up` first.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Api-Key": RADARR_API_KEY}
    print(f"Searching for Movie '{query}' in Radarr...")
    lookup = make_request(f"{RADARR_URL}/movie/lookup?term={urllib.parse.quote(query)}", headers=headers)
    if not lookup:
        print("No matching movies found.", file=sys.stderr)
        return

    movie = lookup[0]
    movie["rootFolderPath"] = "/data/movies"
    movie["qualityProfileId"] = quality_id
    movie["monitored"] = True
    movie["addOptions"] = {"searchForMovie": True}

    print(f"Adding '{movie.get('title')}' ({movie.get('year')}) to Radarr...")
    added = make_request(f"{RADARR_URL}/movie", method="POST", headers=headers, data=movie)
    print(f"✓ Added movie: {added.get('title')}. Radarr will monitor and download it automatically.")


def request_game(query, limit_gb=100.0, auto_confirm=False):
    search_interactive(query, category="games", limit_gb=limit_gb, auto_confirm=auto_confirm)


def main():
    parser = argparse.ArgumentParser(description="Media Stack CLI helper")
    subparsers = parser.add_subparsers(dest="command")

    # TV / Anime parser
    tv_p = subparsers.add_parser("request")
    tv_p.add_argument("query", help="Series name")
    tv_p.add_argument("--type", default="standard", choices=["standard", "anime"])
    tv_p.add_argument("--dub", action="store_true", help="Prefer English Dub / Dual Audio releases")
    tv_p.add_argument("--sub", action="store_true", help="Prefer Subbed (Japanese Audio + English Subtitles) releases (default)")
    tv_p.add_argument("-i", "--interactive", action="store_true", help="Interactively search indexers & pick release manually")

    # Movie parser
    movie_p = subparsers.add_parser("request-movie")
    movie_p.add_argument("query", help="Movie name")
    movie_p.add_argument("-i", "--interactive", action="store_true", help="Interactively search indexers & pick release manually")

    # Game parser
    game_p = subparsers.add_parser("request-game")
    game_p.add_argument("query", help="Game name")
    game_p.add_argument("-y", "--yes", action="store_true", help="Auto-confirm the top result")
    game_p.add_argument("-l", "--limit", type=float, default=100.0, help="Max release size limit in GB")

    # General Search parser
    search_p = subparsers.add_parser("search")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--category", default="tv", choices=["tv", "anime", "movies", "games"])
    search_p.add_argument("-y", "--yes", action="store_true", help="Auto-confirm the top result")
    search_p.add_argument("-l", "--limit", type=float, default=100.0, help="Max release size limit in GB")

    args = parser.parse_args()

    if args.command == "request":
        request_tv(args.query, series_type=args.type, dub=args.dub, interactive=args.interactive)
    elif args.command == "request-movie":
        request_movie(args.query, interactive=args.interactive)
    elif args.command == "request-game":
        request_game(args.query, limit_gb=args.limit, auto_confirm=args.yes)
    elif args.command == "search":
        search_interactive(args.query, category=args.category, limit_gb=args.limit, auto_confirm=args.yes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
