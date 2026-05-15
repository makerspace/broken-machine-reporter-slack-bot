#!/usr/bin/env python3
"""
Interactive setup wizard for configuring rooms in rooms.yaml.

Connects to your Slack workspace, lists available channels, and lets you
pick which ones to use as report targets.

Usage: python3 setup.py
"""

import os
import sys

import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(".envrc")

ROOMS_FILE = os.path.join(os.path.dirname(__file__), "rooms.yaml")


def load_rooms():
    """Load existing rooms from rooms.yaml."""
    if not os.path.exists(ROOMS_FILE):
        return []
    with open(ROOMS_FILE) as f:
        data = yaml.safe_load(f) or {}
    return data.get("rooms") or []


def save_rooms(rooms):
    """Save rooms to rooms.yaml."""
    with open(ROOMS_FILE, "w") as f:
        yaml.dump(
            {"rooms": rooms},
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    print(f"\n✅ Saved {len(rooms)} room(s) to {ROOMS_FILE}")


def fetch_channels(client):
    """Fetch all channels from the workspace (public + private the bot is in)."""
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    channels.sort(key=lambda c: c["name"])
    return channels


def print_rooms(rooms):
    """Print current room configuration."""
    if not rooms:
        print("  (no rooms configured)")
        return
    for i, room in enumerate(rooms, 1):
        print(f"  {i}. {room['name']}  →  {room['channel_id']}")


def wizard():
    """Run the interactive setup wizard."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("❌ SLACK_BOT_TOKEN not set. Configure it in your .envrc file first.")
        sys.exit(1)

    client = WebClient(token=token)

    # Verify connection
    try:
        auth = client.auth_test()
        print(f"🔗 Connected to workspace: {auth['team']}")
    except SlackApiError as e:
        print(f"❌ Could not connect to Slack: {e.response['error']}")
        sys.exit(1)

    rooms = load_rooms()

    while True:
        print("\n── Current rooms ──")
        print_rooms(rooms)

        print("\n── Menu ──")
        print("  1. Add room")
        print("  2. Remove room")
        print("  3. Quit")

        choice = input("\nChoose [1-3]: ").strip()

        if choice == "1":
            rooms = add_room(client, rooms)
        elif choice == "2":
            rooms = remove_room(rooms)
        elif choice == "3":
            print("Done.")
            break
        else:
            print("Invalid choice, try again.")


def add_room(client, rooms):
    """Add a room by selecting a Slack channel."""
    print("\n📡 Fetching channels from Slack...")
    try:
        channels = fetch_channels(client)
    except SlackApiError as e:
        print(f"❌ Could not fetch channels: {e.response['error']}")
        return rooms

    existing_ids = {r["channel_id"] for r in rooms}

    # Filter out already-configured channels
    available = [c for c in channels if c["id"] not in existing_ids]
    if not available:
        print("All channels are already configured!")
        return rooms

    # Show channels with numbers
    print(f"\nAvailable channels ({len(available)}):")
    for i, ch in enumerate(available, 1):
        print(f"  {i:3}. #{ch['name']}  ({ch['id']})")

    selection = input(
        "\nSelect channel number(s) (comma-separated, or 'q' to cancel): "
    ).strip()
    if selection.lower() == "q":
        return rooms

    for num_str in selection.split(","):
        num_str = num_str.strip()
        if not num_str.isdigit():
            print(f"  ⚠️  Invalid: {num_str}")
            continue
        idx = int(num_str) - 1
        if idx < 0 or idx >= len(available):
            print(f"  ⚠️  Out of range: {num_str}")
            continue

        ch = available[idx]
        # Ask for display name
        default_name = ch["name"].replace("-", " ").replace("_", " ").title()
        name = input(f"  Display name for #{ch['name']} [{default_name}]: ").strip()
        if not name:
            name = default_name

        rooms.append({"name": name, "channel_id": ch["id"]})
        print(f"  ✅ Added: {name} → {ch['id']}")

        # Try to join the channel
        try:
            client.conversations_join(channel=ch["id"])
        except SlackApiError:
            pass  # Already a member, or private channel

    save_rooms(rooms)
    return rooms


def remove_room(rooms):
    """Remove a room by number."""
    if not rooms:
        print("No rooms to remove.")
        return rooms

    selection = input("Which room to remove? (number): ").strip()
    if not selection.isdigit():
        print("Invalid choice.")
        return rooms

    idx = int(selection) - 1
    if idx < 0 or idx >= len(rooms):
        print("Out of range.")
        return rooms

    removed = rooms.pop(idx)
    print(f"  🗑️  Removed: {removed['name']}")
    save_rooms(rooms)
    return rooms


if __name__ == "__main__":
    wizard()
