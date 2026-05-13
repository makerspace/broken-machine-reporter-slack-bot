"""
In-memory store mapping anonymous reports to their reporters.

Maps channel thread_ts -> reporter user_id, and tracks DM conversations
so the reporter can reply anonymously.
"""

import threading


class ReportStore:
    """Thread-safe store for anonymous report mappings."""

    def __init__(self):
        self._lock = threading.Lock()
        # (channel_id, thread_ts) -> reporter_user_id
        self._thread_to_reporter: dict[tuple[str, str], str] = {}
        # (dm_channel_id, dm_thread_ts) -> (channel_id, public_thread_ts)
        self._dm_to_thread: dict[tuple[str, str], tuple[str, str]] = {}
        # reporter_user_id -> (dm_channel_id, dm_thread_ts)
        self._reporter_to_dm: dict[str, tuple[str, str]] = {}

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
