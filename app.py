#!/usr/bin/env python3
"""
Stockholm Makerspace — Anonymous Broken Equipment Reporter Bot

Start with: python app.py
"""

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from src.report_flow import register_report_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = App(token=SLACK_BOT_TOKEN)

# Register handlers
register_report_handlers(app)

if __name__ == "__main__":
    logger.info("Starting Stockholm Makerspace Broken Equipment Bot...")
    # App ID is embedded in the app-level token: xapp-1-AXXXXX-...
    parts = SLACK_APP_TOKEN.split("-")
    app_id = parts[2] if len(parts) >= 3 else None
    if app_id:
        logger.info(f"Bot DM link: https://slack.com/app_redirect?app={app_id}")
    else:
        logger.warning("Could not determine app ID for DM link")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
