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
    logger.info("⚡ Starting Stockholm Makerspace Felanmälan Bot...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
