#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Load paths
CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

SONARR_URL = os.environ.get("SONARR_URL", "http://localhost:8989/api/v3")
RADARR_URL = os.environ.get("RADARR_URL", "http://localhost:7878/api/v3")
PROWLARR_URL = os.environ.get("PROWLARR_URL", "http://localhost:9696/api/v1")

QBITTORRENT_HOST = os.environ.get("QBITTORRENT_HOST", "qbittorrent")
QBITTORRENT_PORT = int(os.environ.get("QBITTORRENT_PORT", "8080"))
QBITTORRENT_USER = os.environ.get("QBITTORRENT_USER", "admin")
QBITTORRENT_PASSWORD = os.environ.get("QBITTORRENT_PASSWORD", "adminadmin")

PROWLARR_INDEXERS = [
    item.strip()
    for item in os.environ.get(
        "PROWLARR_INDEXERS",
        "1337x,Nyaa.si,TorrentGalaxy,EZTV,YTS,RuTracker",
    ).split(",")
    if item.strip()
]
PROWLARR_APP_PROFILE_ID = int(os.environ.get("PROWLARR_APP_PROFILE_ID", "1"))


def get_api_key_from_xml(config_file):
    if not os.path.exists(config_file):
        return None
    try:
        tree = ET.parse(config_file)
        root = tree.getroot()
        api_key_elem = root.find("ApiKey")
        if api_key_elem is not None:
            return api_key_elem.text
    except Exception as e:
        print(f"Error reading {config_file}: {e}")
    return None


def extract_or_load_keys():
    keys = {
        "SONARR_API_KEY": os.environ.get("SONARR_API_KEY") or get_api_key_from_xml(os.path.join(CONFIG_DIR, "sonarr", "config.xml")),
        "RADARR_API_KEY": os.environ.get("RADARR_API_KEY") or get_api_key_from_xml(os.path.join(CONFIG_DIR, "radarr", "config.xml")),
        "PROWLARR_API_KEY": os.environ.get("PROWLARR_API_KEY") or get_api_key_from_xml(os.path.join(CONFIG_DIR, "prowlarr", "config.xml")),
    }
    return keys


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


def wait_for_apis(keys):
    print("Waiting for Sonarr, Radarr, and Prowlarr services to become responsive...")
    for _ in range(45):
        try:
            if keys.get("SONARR_API_KEY"):
                make_request(f"{SONARR_URL}/system/status", headers={"X-Api-Key": keys["SONARR_API_KEY"]})
            if keys.get("RADARR_API_KEY"):
                make_request(f"{RADARR_URL}/system/status", headers={"X-Api-Key": keys["RADARR_API_KEY"]})
            if keys.get("PROWLARR_API_KEY"):
                make_request(f"{PROWLARR_URL}/system/status", headers={"X-Api-Key": keys["PROWLARR_API_KEY"]})
            print("✓ All services are online and responding.")
            return True
        except Exception:
            time.sleep(2)
    return False


def find_schema(items, implementation=None, name=None):
    for item in items:
        if implementation and item.get("implementation") == implementation:
            return item
        if name and item.get("name") == name:
            return item
    return None


def configure_download_client(api_url, api_key, app_name, category):
    print(f"Configuring qBittorrent download client in {app_name}...")
    headers = {"X-Api-Key": api_key}
    try:
        existing = make_request(f"{api_url}/downloadclient", headers=headers)
        for client in existing:
            if client.get("name") == "qBittorrent":
                print(f"✓ qBittorrent is already configured in {app_name}.")
                return
    except Exception:
        pass

    schema_list = make_request(f"{api_url}/downloadclient/schema", headers=headers)
    schema = find_schema(schema_list, implementation="QBittorrent")
    if not schema:
        print(f"Could not find QBittorrent schema for {app_name}.")
        return

    for field in schema["fields"]:
        if field["name"] == "host":
            field["value"] = QBITTORRENT_HOST
        elif field["name"] == "port":
            field["value"] = QBITTORRENT_PORT
        elif field["name"] == "username":
            field["value"] = QBITTORRENT_USER
        elif field["name"] == "password":
            field["value"] = QBITTORRENT_PASSWORD
        elif field["name"] in ("tvCategory", "movieCategory"):
            field["value"] = category

    schema["name"] = "qBittorrent"
    schema["enable"] = True
    make_request(f"{api_url}/downloadclient", method="POST", headers=headers, data=schema)
    print(f"✓ Configured qBittorrent in {app_name}.")


def configure_prowlarr_apps(prowlarr_key, sonarr_key, radarr_key):
    print("Linking Sonarr and Radarr applications into Prowlarr...")
    headers = {"X-Api-Key": prowlarr_key}
    schema_list = make_request(f"{PROWLARR_URL}/applications/schema", headers=headers)

    # Link Sonarr
    if sonarr_key:
        schema = find_schema(schema_list, implementation="Sonarr")
        if schema:
            for field in schema["fields"]:
                if field["name"] == "prowlarrUrl":
                    field["value"] = "http://prowlarr:9696"
                elif field["name"] == "baseUrl":
                    field["value"] = "http://sonarr:8989"
                elif field["name"] == "apiKey":
                    field["value"] = sonarr_key
            schema["name"] = "Sonarr"
            schema["syncLevel"] = "fullSync"
            make_request(f"{PROWLARR_URL}/applications", method="POST", headers=headers, data=schema)
            print("✓ Linked Sonarr in Prowlarr.")

    # Link Radarr
    if radarr_key:
        schema = find_schema(schema_list, implementation="Radarr")
        if schema:
            for field in schema["fields"]:
                if field["name"] == "prowlarrUrl":
                    field["value"] = "http://prowlarr:9696"
                elif field["name"] == "baseUrl":
                    field["value"] = "http://radarr:7878"
                elif field["name"] == "apiKey":
                    field["value"] = radarr_key
            schema["name"] = "Radarr"
            schema["syncLevel"] = "fullSync"
            make_request(f"{PROWLARR_URL}/applications", method="POST", headers=headers, data=schema)
            print("✓ Linked Radarr in Prowlarr.")


def configure_prowlarr_indexers(prowlarr_key):
    print("Adding safe default indexers in Prowlarr...")
    headers = {"X-Api-Key": prowlarr_key}
    
    existing = make_request(f"{PROWLARR_URL}/indexer", headers=headers)
    existing_names = {idx.get("name") for idx in existing}

    schemas = make_request(f"{PROWLARR_URL}/indexer/schema", headers=headers, timeout=30)

    for tracker_name in PROWLARR_INDEXERS:
        if tracker_name in existing_names:
            print(f"✓ Indexer '{tracker_name}' is already added.")
            continue

        schema = find_schema(schemas, name=tracker_name)
        if not schema:
            print(f"Notice: Could not find schema for indexer '{tracker_name}'")
            continue

        schema["enable"] = True
        schema["appProfileId"] = PROWLARR_APP_PROFILE_ID
        try:
            make_request(f"{PROWLARR_URL}/indexer", method="POST", headers=headers, data=schema)
            print(f"✓ Added indexer: {tracker_name}")
        except Exception as e:
            print(f"Skipping indexer '{tracker_name}' due to error: {e}")


def update_env_keys(keys):
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r") as f:
        content = f.read()

    for k, v in keys.items():
        if v:
            pattern = re.compile(rf"^{k}=.*$", re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f"{k}={v}", content)
            else:
                content += f"\n{k}={v}"

    with open(ENV_PATH, "w") as f:
        f.write(content)


def main():
    keys = extract_or_load_keys()
    if not any(keys.values()):
        print("Waiting for containers to generate initial configuration files...")
        time.sleep(5)
        keys = extract_or_load_keys()

    update_env_keys(keys)

    if not wait_for_apis(keys):
        print("Could not connect to services. Provisioning deferred.", file=sys.stderr)
        return 1

    if keys.get("SONARR_API_KEY"):
        configure_download_client(SONARR_URL, keys["SONARR_API_KEY"], "Sonarr", "tv")
    if keys.get("RADARR_API_KEY"):
        configure_download_client(RADARR_URL, keys["RADARR_API_KEY"], "Radarr", "movies")

    if keys.get("PROWLARR_API_KEY"):
        configure_prowlarr_apps(keys["PROWLARR_API_KEY"], keys.get("SONARR_API_KEY"), keys.get("RADARR_API_KEY"))
        configure_prowlarr_indexers(keys["PROWLARR_API_KEY"])

    print("\n🎉 Provisioning complete! All safe indexers and download client links are ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
