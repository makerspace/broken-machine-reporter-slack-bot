"""
Persistent store mapping anonymous reports to their reporters.

Maps channel thread_ts -> reporter user_id, and tracks DM conversations
so the reporter can reply anonymously. Data is persisted to a JSON file
so mappings survive bot restarts.
"""

import json
import os
import threading

STORE_FILE = os.path.join(os.path.dirname(__file__), "report_store.json")


class ReportStore:
    """Thread-safe, file-backed store for anonymous report mappings."""

    def __init__(self, path: str = STORE_FILE):
        self._lock = threading.Lock()
        self._path = path
        # (channel_id, thread_ts) -> reporter_user_id
        self._thread_to_reporter: dict[tuple[str, str], str] = {}
        # (dm_channel_id, dm_thread_ts) -> (channel_id, public_thread_ts)
        self._dm_to_thread: dict[tuple[str, str], tuple[str, str]] = {}
        # reporter_user_id -> (dm_channel_id, dm_thread_ts)
        self._reporter_to_dm: dict[str, tuple[str, str]] = {}
        self._load()

    def _load(self):
        """Load state from disk."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            for entry in data.get("reports", []):
                ch = entry["channel_id"]
                ts = entry["thread_ts"]
                uid = entry["reporter_user_id"]
                dm_ch = entry["dm_channel_id"]
                dm_ts = entry["dm_message_ts"]
                self._thread_to_reporter[(ch, ts)] = uid
                self._dm_to_thread[(dm_ch, dm_ts)] = (ch, ts)
                self._reporter_to_dm[uid] = (dm_ch, dm_ts)
        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self):
        """Persist current state to disk. Must be called with lock held."""
        reports = []
        for (ch, ts), uid in self._thread_to_reporter.items():
            dm_info = self._reporter_to_dm.get(uid)
            if dm_info:
                reports.append({
                    "channel_id": ch,
                    "thread_ts": ts,
                    "reporter_user_id": uid,
                    "dm_channel_id": dm_info[0],
                    "dm_message_ts": dm_info[1],
                })
        with open(self._path, "w") as f:
            json.dump({"reports": reports}, f, indent=2)

    def register_report(
        self,
        channel_id: str,
        thread_ts: str,
        reporter_user_id: str,
        dm_channel_id: str,
        dm_message_ts: str,
    ):
        """Register a new anonymous report."""
        with self._lock:
            self._thread_to_reporter[(channel_id, thread_ts)] = reporter_user_id
            self._dm_to_thread[(dm_channel_id, dm_message_ts)] = (channel_id, thread_ts)
            self._reporter_to_dm[reporter_user_id] = (dm_channel_id, dm_message_ts)
            self._save()

    def get_reporter(self, channel_id: str, thread_ts: str) -> str | None:
        """Get the reporter user_id for a public thread."""
        with self._lock:
            return self._thread_to_reporter.get((channel_id, thread_ts))

    def get_public_thread(self, dm_channel_id: str, dm_thread_ts: str) -> tuple[str, str] | None:
        """Get the (channel_id, thread_ts) for a DM thread."""
        with self._lock:
            return self._dm_to_thread.get((dm_channel_id, dm_thread_ts))

    def get_dm_info(self, reporter_user_id: str) -> tuple[str, str] | None:
        """Get (dm_channel_id, dm_thread_ts) for a reporter."""
        with self._lock:
            return self._reporter_to_dm.get(reporter_user_id)


store = ReportStore()
