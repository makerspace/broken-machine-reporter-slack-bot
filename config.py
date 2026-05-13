import os

from dotenv import load_dotenv

load_dotenv(".envrc")

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# Room name -> Slack channel ID mapping
ROOMS: dict[str, str] = {
    "3d-skrivarrummet": os.environ.get("CHANNEL_3D_SKRIVARRUMMET", ""),
    "elektronikrummet": os.environ.get("CHANNEL_ELEKTRONIKRUMMET", ""),
    "lagerrummet": os.environ.get("CHANNEL_LAGERRUMMET", ""),
    "metallrummet": os.environ.get("CHANNEL_METALLRUMMET", ""),
    "silversmidesrummet": os.environ.get("CHANNEL_SILVERSMIDESRUMMET", ""),
    "stora_rummet": os.environ.get("CHANNEL_STORA_RUMMET", ""),
    "svetsrummet": os.environ.get("CHANNEL_SVETSRUMMET", ""),
    "textilrummet": os.environ.get("CHANNEL_TEXTILRUMMET", ""),
    "trarummet": os.environ.get("CHANNEL_TRARUMMET", ""),
    "vatrummet": os.environ.get("CHANNEL_VATRUMMET", ""),
}

# Display names for rooms (used in the UI)
ROOM_DISPLAY_NAMES: dict[str, str] = {
    "3d-skrivarrummet": "3D-skrivarrummet (3D printing room)",
    "elektronikrummet": "Elektronikrummet (electronics room)",
    "lagerrummet": "Lagerrummet (storage room)",
    "metallrummet": "Metallrummet (metal room)",
    "silversmidesrummet": "Silversmidesrummet (silversmithing room)",
    "stora_rummet": "Stora rummet (large room)",
    "svetsrummet": "Svetsrummet (welding room)",
    "textilrummet": "Textilrummet (textile room)",
    "trarummet": "Trärummet (wood room)",
    "vatrummet": "Våtrummet (wet room)",
}
