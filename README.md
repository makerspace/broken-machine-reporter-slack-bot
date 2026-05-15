# Stockholm Makerspace — Broken Equipment Bot 🔧

A Slack bot for anonymously reporting broken machines and tools at Stockholm Makerspace. Users scan a QR code, fill in a report, and the bot posts it anonymously to the relevant room channel. Two-way anonymous communication is supported via thread replies.

## How it works

1. **User scans a QR code** → opens the bot's DM in Slack
2. **Bot immediately prompts** the user with a "Report broken equipment" button (via the `app_home_opened` event)
3. **User clicks the button** → a modal opens with:
   - A dropdown to select which room the broken thing is in
   - A text field to describe the problem
   - An optional image upload (up to 3 files)
4. **Bot posts the report anonymously** to the selected room's Slack channel (with an "Image in thread 🧵" note if images were attached)
5. **Thread replies are relayed**: anyone replying in the public thread gets their message forwarded privately to the anonymous reporter (with a mention so they get notified)
6. **Reporter can reply back** in their DM thread, and the bot relays it anonymously to the public thread
7. **Prompt cleanup**: the bot deletes its prompt messages after the user clicks the button, and stale prompts are automatically cleaned up after 30 minutes

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it something like `Broken Equipment Bot`

### 2. Configure Permissions

Under **OAuth & Permissions → Bot Token Scopes**, add:

- `chat:write` — post and delete messages
- `channels:join` — auto-join configured channels
- `channels:read` — list workspace channels (for setup wizard)
- `channels:history` — receive public channel messages
- `groups:history` — receive private channel messages
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

- `app_home_opened` — triggers the report prompt when a user opens the bot
- `message.im` — DM messages
- `message.channels` — public channel messages (for thread replies)
- `message.groups` — private channel messages (for thread replies)
- `app_mention` — mentions of the bot

### 5. Enable Interactivity & App Home

1. Under **Interactivity & Shortcuts**, toggle **Interactivity** on (Socket Mode handles the URL automatically)
2. Under **App Home → Show Tabs**, enable the **Messages Tab** and check **"Allow users to send Slash commands and messages from the messages tab"**

### 6. Install the App

1. Go to **Install App** → **Install to Workspace**
2. Copy the **Bot User OAuth Token** (`xoxb-...`) — save as `SLACK_BOT_TOKEN`

### 7. Configure Environment

```bash
cp .env.example .envrc
```

Edit `.envrc` with your Slack tokens.

### 8. Install & Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 9. Configure Rooms

Run the interactive setup wizard to select which Slack channels map to rooms:

```bash
python3 setup.py
```

The wizard connects to your workspace, lists all channels, and lets you pick which ones to use. Room configuration is saved to `rooms.yaml`. You can re-run it anytime to add or remove rooms.

### 10. Start the Bot

```bash
python3 app.py
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
app.py              — Entry point, starts Socket Mode
src/config.py       — Environment config, loads rooms.yaml
src/store.py        — JSON-backed persistent store for report↔reporter mappings
src/report_flow.py  — Report modal, submission, anonymous posting, prompt cleanup
src/relay.py        — Two-way message relay between threads and DMs
setup.py            — Interactive wizard for configuring rooms
rooms.yaml          — Room→channel mapping (edited via setup.py)
```

## Adding / Removing Rooms

Run the setup wizard:

```bash
python3 setup.py
```

Or edit `rooms.yaml` directly:

```yaml
rooms:
  - name: "Electronics Room"
    channel_id: "C017ZQEHK7Z"
  - name: "Woodworking Room"
    channel_id: "C0123456789"
```

Restart the bot after changing rooms.

## Notes

- Report mappings are **persisted to `report_store.json`** so thread relay continues working across bot restarts.
- The reporter's identity is **never revealed** in public channels.
- File re-uploads ensure images appear from the bot, not the reporter.
- Prompt messages are cleaned up automatically (on button click, or after 30 minutes if unused).
- Duplicate prompts are avoided: if a pending prompt exists, `app_home_opened` won't create another.

## Future ideas

- Collect feedback/ideas
- Store the collection of all reported things
- Let people view and vote on what they think is important
