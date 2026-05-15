import os

import yaml
from dotenv import load_dotenv

load_dotenv(".envrc")

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# Load room configuration from rooms.yaml
_ROOMS_FILE = os.path.join(os.path.dirname(__file__), "rooms.yaml")


def _load_rooms_yaml():
    if not os.path.exists(_ROOMS_FILE):
        return {}, {}
    with open(_ROOMS_FILE) as f:
        data = yaml.safe_load(f) or {}
    rooms = {}
    display_names = {}
    for entry in data.get("rooms") or []:
        name = entry["name"]
        channel_id = entry["channel_id"]
        key = name.lower().replace(" ", "_").replace("-", "_")
        rooms[key] = channel_id
        display_names[key] = name
    return rooms, display_names


ROOMS, ROOM_DISPLAY_NAMES = _load_rooms_yaml()
