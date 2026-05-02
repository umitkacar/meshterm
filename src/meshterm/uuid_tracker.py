"""UUID tracking for meshterm sessions.

Maps human-readable names and UUIDs to tmux pane IDs.
Storage: Redis (primary, shared across machines) + local file (fallback).

tmux pane IDs (%0, %1...) are server-scoped and not true UUIDs.
This module bridges that gap with persistent UUID mapping.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Optional


class UUIDTracker:
    """Persistent UUID ↔ pane_id mapping.

    Two storage backends (tried in order):
    1. Redis (shared, cross-machine, fast)
    2. Local JSON file (always works, single-machine)

    Usage:
        tracker = UUIDTracker(redis_url="redis://:changeme@localhost:6379")
        uid = tracker.register("worker-1", "%0")
        pane_id = tracker.resolve(uid)
        tracker.unregister(uid)
    """

    REDIS_PREFIX = "meshterm:uuid:"
    LOCAL_FILE = "~/.config/meshterm/uuid_map.json"

    def __init__(
        self,
        redis_url: str | None = None,
        local_file: str | None = None,
    ):
        self._redis = None
        self._local_path = Path(os.path.expanduser(local_file or self.LOCAL_FILE))
        self._local_path.parent.mkdir(parents=True, exist_ok=True)

        if redis_url:
            try:
                import redis
                self._redis = redis.from_url(redis_url)
                self._redis.ping()
            except Exception:
                self._redis = None

        self._local_cache: dict[str, dict] = self._load_local()

    # ── Public API ──

    def register(self, name: str, pane_id: str) -> str:
        """Register a pane with a name, return UUID."""
        uid = str(uuid.uuid4())
        entry = {
            "uuid": uid,
            "name": name,
            "pane_id": pane_id,
        }

        # Redis (primary)
        if self._redis:
            try:
                self._redis.set(
                    f"{self.REDIS_PREFIX}{uid}",
                    json.dumps(entry),
                )
                self._redis.set(
                    f"{self.REDIS_PREFIX}name:{name}",
                    uid,
                )
            except Exception:
                pass

        # Local (always)
        self._local_cache[uid] = entry
        self._save_local()

        return uid

    def resolve(self, uid: str) -> str | None:
        """Resolve UUID to pane_id."""
        # Redis first
        if self._redis:
            try:
                data = self._redis.get(f"{self.REDIS_PREFIX}{uid}")
                if data:
                    return json.loads(data)["pane_id"]
            except Exception:
                pass

        # Local fallback
        entry = self._local_cache.get(uid)
        return entry["pane_id"] if entry else None

    def resolve_by_name(self, name: str) -> str | None:
        """Resolve name to UUID."""
        # Redis first
        if self._redis:
            try:
                uid = self._redis.get(f"{self.REDIS_PREFIX}name:{name}")
                if uid:
                    return uid.decode() if isinstance(uid, bytes) else uid
            except Exception:
                pass

        # Local fallback
        for uid, entry in self._local_cache.items():
            if entry.get("name") == name:
                return uid
        return None

    def unregister(self, uid: str) -> None:
        """Remove UUID mapping."""
        entry = self._local_cache.pop(uid, None)

        if self._redis:
            try:
                self._redis.delete(f"{self.REDIS_PREFIX}{uid}")
                if entry:
                    self._redis.delete(f"{self.REDIS_PREFIX}name:{entry['name']}")
            except Exception:
                pass

        self._save_local()

    def list_all(self) -> list[dict]:
        """List all registered sessions."""
        return list(self._local_cache.values())

    # ── Local file storage ──

    def _load_local(self) -> dict:
        if self._local_path.exists():
            try:
                return json.loads(self._local_path.read_text())
            except Exception:
                return {}
        return {}

    def _save_local(self) -> None:
        try:
            self._local_path.write_text(json.dumps(self._local_cache, indent=2))
        except Exception:
            pass
