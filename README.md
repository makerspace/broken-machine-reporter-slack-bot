# Stockholm Makerspace — Felanmälan Bot 🔧

A Slack bot for anonymously reporting broken machines and tools at Stockholm Makerspace. Users scan a QR code, fill in a report, and the bot posts it anonymously to the relevant room channel. Two-way anonymous communication is supported via thread replies.

## How it works

1. **User scans a QR code** → opens a DM with the bot in Slack
2. **User clicks "Rapportera trasigt"** → a modal opens with:
   - A dropdown to select which room the broken thing is in
   - A text field to describe the problem
   - An optional image upload
3. **Bot posts the report anonymously** to the selected room's Slack channel
4. **Thread replies are relayed**: anyone replying in the public thread gets their message forwarded privately to the anonymous reporter
5. **Reporter can reply back** in their DM thread, and the bot relays it anonymously to the public thread

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it something like `Felanmälan Bot`

### 2. Configure Permissions

Under **OAuth & Permissions → Bot Token Scopes**, add:

- `chat:write` — post messages
- `im:history` — read DM messages
- `im:write` — send DMs
- `files:read` — read uploaded files
- `files:write` — upload files to channels
- `users:read` — get user display names for relay

### 3. Enable Socket Mode

1. Go to **Settings → Socket Mode** → toggle **Enable Socket Mode**
2. Create an **App-Level Token** with scope `connections:write` — save this as `SLACK_APP_TOKEN`

### 4. Enable Events

Under **Event Subscriptions → Subscribe to bot events**, add:

- `message.im` — DM messages
- `message.channels` — public channel messages (for thread replies)
- `app_mention` — mentions of the bot

### 5. Enable Interactivity

Under **Interactivity & Shortcuts**, toggle **Interactivity** on (Socket Mode handles the URL automatically).

### 6. Install the App

1. Go to **Install App** → **Install to Workspace**
2. Copy the **Bot User OAuth Token** (`xoxb-...`) — save as `SLACK_BOT_TOKEN`
3. **Invite the bot** to each room channel (e.g. `/invite @Felanmälan Bot` in each channel)

### 7. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your tokens and channel IDs. Find channel IDs by right-clicking a channel → **View channel details** → scroll to the bottom.

### 8. Install & Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## QR Code Setup

Generate a QR code that links to:

```
https://slack.com/app_redirect?app=YOUR_APP_ID
```

Replace `YOUR_APP_ID` with your Slack app's ID (found under **Basic Information** in your app settings). When scanned on a phone with Slack installed, this opens a DM with the bot.

Print and place QR codes near machines/rooms at the makerspace.

## Architecture

```
app.py          — Entry point, starts Socket Mode
config.py       — Environment config, room→channel mapping
store.py        — In-memory store for report↔reporter mappings
report_flow.py  — Report modal, submission, anonymous posting
relay.py        — Two-way message relay between threads and DMs
```

## Adding Rooms

1. Create the Slack channel for the room
2. Invite the bot to the channel
3. Add the channel ID to `.env` (e.g. `CHANNEL_NYTT_RUM=C0123456789`)
4. Add the room to `ROOMS` and `ROOM_DISPLAY_NAMES` in `config.py`

## Notes

- Reports are stored **in memory only** — restarting the bot clears the mappings (existing threads will no longer relay). For persistence, swap `store.py` for a database-backed implementation.
- The reporter's identity is **never revealed** in public channels.
- File re-uploads ensure images appear from the bot, not the reporter.
