"""
Handlers for the report flow:
- QR code deep link opens DM -> bot starts conversation
- User fills in a modal with room, description, and optional image
- Bot posts the report anonymously to the room's channel
"""

import logging
import threading
import time

import requests
from slack_bolt import App

from src.config import ROOM_DISPLAY_NAMES, ROOMS, SLACK_BOT_TOKEN
from src.relay import handle_thread_reply
from src.store import store

logger = logging.getLogger(__name__)

# Track prompt messages: user_id -> list of (channel, ts, created_at)
_prompt_messages: dict[str, list[tuple[str, str, float]]] = {}
_prompt_lock = threading.Lock()

PROMPT_TIMEOUT_SECONDS = 30 * 60  # 30 minutes


def _track_prompt(user_id: str, channel: str, ts: str):
    """Track a prompt message so it can be deleted later."""
    with _prompt_lock:
        _prompt_messages.setdefault(user_id, []).append((channel, ts, time.time()))


def _has_pending_prompt(user_id: str) -> bool:
    """Check if a user already has an active prompt."""
    with _prompt_lock:
        return bool(_prompt_messages.get(user_id))


def _delete_prompts(client, user_id: str):
    """Delete all tracked prompt messages for a user."""
    with _prompt_lock:
        messages = _prompt_messages.pop(user_id, [])
    for channel, ts, _ in messages:
        try:
            client.chat_delete(channel=channel, ts=ts)
        except Exception:
            logger.debug("Could not delete prompt message %s in %s", ts, channel)


def _start_cleanup_thread(app: App):
    """Background thread that deletes stale prompt messages."""

    def _cleanup_loop():
        while True:
            time.sleep(60)  # check every minute
            now = time.time()
            stale_users = []
            with _prompt_lock:
                for user_id, messages in _prompt_messages.items():
                    if all(
                        now - created > PROMPT_TIMEOUT_SECONDS
                        for _, _, created in messages
                    ):
                        stale_users.append(user_id)
            for user_id in stale_users:
                with _prompt_lock:
                    messages = _prompt_messages.pop(user_id, [])
                for channel, ts, _ in messages:
                    try:
                        app.client.chat_delete(channel=channel, ts=ts)
                    except Exception:
                        logger.debug(
                            "Could not delete stale prompt %s in %s", ts, channel
                        )
                logger.info("Cleaned up stale prompts for user %s", user_id)

    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()


def register_report_handlers(app: App):
    """Register all report-flow handlers on the Slack Bolt app."""

    _start_cleanup_thread(app)

    # ── 1. Entry point: user opens a DM (via QR deep link) ──────────────
    # The QR code links to: https://slack.com/app_redirect?app=<APP_ID>
    # which opens the bot's DM. The user sends any message (or clicks the
    # Home tab) and we respond with a prompt to start a report.

    @app.event("app_home_opened")
    def handle_app_home(event, client):
        """User opened the bot's App Home / Messages tab — send the report prompt."""
        user_id = event["user"]
        tab = event.get("tab")
        logger.info("app_home_opened: user=%s tab=%s", user_id, tab)

        # Only trigger on the "messages" tab (DM view), not the "home" tab
        if tab != "messages":
            return

        # Don't send a new prompt if one is already pending
        if _has_pending_prompt(user_id):
            logger.info(
                "Skipping prompt for %s — already has a pending prompt", user_id
            )
            return

        result = client.chat_postMessage(
            channel=user_id,
            text="Hi! Want to report something broken? Click the button below.",
            blocks=_start_blocks(),
        )
        _track_prompt(user_id, result["channel"], result["ts"])

    @app.event("app_mention")
    def handle_mention(event, client):
        result = client.chat_postMessage(
            channel=event["channel"],
            text="Hi! Want to report something broken? Click the button below.",
            blocks=_start_blocks(),
        )
        _track_prompt(event["user"], result["channel"], result["ts"])

    @app.event("message")
    def handle_dm(event, say, client):
        logger.info("Received message event: %s", event)

        # Threaded replies go to the relay handler (works for both DMs and channels)
        if event.get("thread_ts") and event.get("thread_ts") != event.get("ts"):
            logger.info(
                "Routing to thread reply handler (thread_ts=%s)", event.get("thread_ts")
            )
            handle_thread_reply(event, client)
            return

        # Only respond to direct messages (im), ignore bot messages
        channel_id = event.get("channel")
        if event.get("channel_type") != "im":
            logger.info(
                "Ignoring non-DM message (channel_type=%s)", event.get("channel_type")
            )
            return
        if event.get("bot_id") or event.get("subtype"):
            logger.info(
                "Ignoring bot/subtype message (bot_id=%s, subtype=%s)",
                event.get("bot_id"),
                event.get("subtype"),
            )
            return

        result = client.chat_postMessage(
            channel=channel_id,
            text="Hi! Want to report something broken? Click the button below.",
            blocks=_start_blocks(),
        )
        _track_prompt(event["user"], result["channel"], result["ts"])

    # ── 2. "Report broken" button opens a modal ────────────────────────

    @app.action("open_report_modal")
    def handle_open_modal(ack, body, client):
        ack()
        # Delete the prompt messages now that the user clicked the button
        user_id = body["user"]["id"]
        _delete_prompts(client, user_id)
        client.views_open(
            trigger_id=body["trigger_id"],
            view=_report_modal(),
        )

    # ── 3. Modal submission → post anonymous report ────────────────────

    @app.view("report_modal_submit")
    def handle_modal_submit(ack, body, client, view):
        ack()

        values = view["state"]["values"]
        room_key = values["room_select"]["room_choice"]["selected_option"]["value"]
        description = values["description_block"]["description_input"]["value"]

        # The file upload is handled by Slack's file_input block
        files = values.get("image_block", {}).get("image_input", {}).get("files", [])

        reporter_user_id = body["user"]["id"]
        channel_id = ROOMS.get(room_key)
        room_name = ROOM_DISPLAY_NAMES.get(room_key, room_key)

        if not channel_id:
            client.chat_postMessage(
                channel=reporter_user_id,
                text=f"❌ The channel for {room_name} is not configured. Contact an admin.",
            )
            return

        # Build the anonymous report message
        report_blocks = _report_message_blocks(
            room_name, description, has_image=bool(files)
        )

        # Post the anonymous report to the room channel
        result = client.chat_postMessage(
            channel=channel_id,
            text=f"🔧 Broken equipment report in {room_name}: {description}",
            blocks=report_blocks,
            unfurl_links=False,
        )
        thread_ts = result["ts"]

        # If there are uploaded files, download and re-upload them to the channel
        # so they appear from the bot (keeping the reporter anonymous)
        if files:
            for file_info in files:
                _reupload_file_to_channel(client, file_info, channel_id, thread_ts)

        # Send confirmation DM to the reporter, this message also becomes the
        # anchor for relaying thread replies back to the reporter
        dm_result = client.chat_postMessage(
            channel=reporter_user_id,
            text=(
                f"<@{reporter_user_id}> ✅ Thanks! Your report has been sent anonymously to *{room_name}*."
                f"\n\nIf someone replies in the thread, I'll forward the reply here. "
                f"You can reply back anonymously by responding in this thread."
            ),
        )

        # Register the mapping so we can relay messages
        store.register_report(
            channel_id=channel_id,
            thread_ts=thread_ts,
            reporter_user_id=reporter_user_id,
            dm_channel_id=dm_result["channel"],
            dm_message_ts=dm_result["ts"],
        )

        logger.info(
            "Report registered: channel=%s thread=%s reporter=%s",
            channel_id,
            thread_ts,
            reporter_user_id,
        )


def _start_blocks():
    """Blocks shown when a user first messages the bot."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "👋 *Hi! Welcome to the broken equipment reporter at Stockholm Makerspace.*\n\n"
                    "Found a broken machine or tool? "
                    "Click the button below to report it anonymously."
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔧 Report broken equipment",
                        "emoji": True,
                    },
                    "action_id": "open_report_modal",
                    "style": "danger",
                }
            ],
        },
    ]


def _report_modal():
    """The modal view for submitting a broken-thing report."""
    room_options = [
        {
            "text": {"type": "plain_text", "text": display_name},
            "value": key,
        }
        for key, display_name in ROOM_DISPLAY_NAMES.items()
        if ROOMS.get(key)
    ]

    return {
        "type": "modal",
        "callback_id": "report_modal_submit",
        "title": {"type": "plain_text", "text": "Report broken equipment"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Fill in the details about what's broken. Your report will be sent anonymously.",
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "room_select",
                "label": {"type": "plain_text", "text": "Which room?"},
                "element": {
                    "type": "static_select",
                    "action_id": "room_choice",
                    "placeholder": {"type": "plain_text", "text": "Select room..."},
                    "options": room_options,
                },
            },
            {
                "type": "input",
                "block_id": "description_block",
                "label": {"type": "plain_text", "text": "What's broken?"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Describe the problem, e.g. which machine/tool and what happened...",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "image_block",
                "label": {"type": "plain_text", "text": "Attach image (optional)"},
                "optional": True,
                "element": {
                    "type": "file_input",
                    "action_id": "image_input",
                    "filetypes": ["png", "jpg", "jpeg", "gif", "webp", "heic"],
                    "max_files": 3,
                },
            },
        ],
    }


def _report_message_blocks(room_name: str, description: str, has_image: bool = False):
    """Build Block Kit blocks for the anonymous report posted to a channel."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔧 Broken Equipment Report",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Room:*\n{room_name}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{description}",
            },
        },
    ]
    if has_image:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📷 *Image in thread* 🧵",
            },
        })
    blocks.extend([
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "📌 This report was sent anonymously. "
                        "Reply in the thread if you have questions — your reply will be forwarded to the reporter. "
                        "Please be kind and constructive! 🙏"
                    ),
                }
            ],
        },
    ])
    return blocks


def _reupload_file_to_channel(client, file_info, channel_id, thread_ts):
    """Download a file from Slack and re-upload it to the target channel."""
    try:
        file_url = file_info.get("url_private_download") or file_info.get("url_private")
        if not file_url:
            logger.warning("No download URL for file: %s", file_info.get("id"))
            return

        # Download the file using the bot token for auth
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        resp = requests.get(file_url, headers=headers, timeout=30)
        resp.raise_for_status()

        # Upload to the channel thread
        client.files_upload_v2(
            channel=channel_id,
            thread_ts=thread_ts,
            file_uploads=[
                {
                    "content": resp.content,
                    "filename": file_info.get("name", "image.jpg"),
                    "title": file_info.get("title", "Attached image"),
                }
            ],
            initial_comment="📷 Attached image from report:",
        )
    except Exception:
        logger.exception("Failed to re-upload file to channel %s", channel_id)
