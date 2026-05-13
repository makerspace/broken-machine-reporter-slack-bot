"""
Message relay system for anonymous two-way communication.

- When someone replies in a public thread → forward to the reporter's DM
- When the reporter replies in their DM thread → forward to the public thread
"""

import logging

from store import store

logger = logging.getLogger(__name__)


def handle_thread_reply(event, client):
    """Handle thread replies for relaying between public channels and DMs.

    Called from the main message handler in report_flow.py.
    """
    # Only handle thread replies (not top-level messages)
    if not event.get("thread_ts") or event.get("thread_ts") == event.get("ts"):
        return
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_id = event["channel"]
    thread_ts = event["thread_ts"]
    user_id = event.get("user")
    text = event.get("text", "")

    # ── Case 1: reply in a PUBLIC channel thread ────────────────────
    reporter = store.get_reporter(channel_id, thread_ts)
    if reporter:
        # Don't relay the reporter's own messages (shouldn't happen in
        # public channel since they're anonymous, but just in case)
        if user_id == reporter:
            return

        dm_info = store.get_dm_info(reporter)
        if not dm_info:
            logger.warning("No DM info found for reporter %s", reporter)
            return

        dm_channel, dm_thread_ts = dm_info

        # Get the display name of the person replying
        try:
            user_info = client.users_info(user=user_id)
            display_name = (
                user_info["user"]["profile"].get("display_name")
                or user_info["user"]["profile"].get("real_name")
                or user_id
            )
        except Exception:
            display_name = "Någon"

        relay_text = f"💬 *{display_name}* svarade i tråden:\n\n{text}"

        # Forward any attached files
        files = event.get("files", [])
        if files:
            relay_text += "\n\n_(meddelandet innehöll bifogade filer som inte kunde vidarebefordras)_"

        client.chat_postMessage(
            channel=dm_channel,
            thread_ts=dm_thread_ts,
            text=relay_text,
        )

        logger.info("Relayed public reply from %s to reporter DM", user_id)
        return

    # ── Case 2: reply in a DM thread (reporter replying back) ──────
    public_thread = store.get_public_thread(channel_id, thread_ts)
    if public_thread:
        pub_channel, pub_thread_ts = public_thread

        relay_text = f"💬 *Anonym rapportör* svarade:\n\n{text}"

        client.chat_postMessage(
            channel=pub_channel,
            thread_ts=pub_thread_ts,
            text=relay_text,
        )

        logger.info("Relayed anonymous reply from reporter to public thread")
        return
