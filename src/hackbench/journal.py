"""Append-only, hash-chained JSONL run journal: every tool call and verdict, tamper-evident."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _digest(prev_hash: str, body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((prev_hash + canonical).encode()).hexdigest()


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        entries = _read(path)
        self._seq = len(entries)
        self._prev = entries[-1]["hash"] if entries else GENESIS

    def append(self, event: dict[str, Any]) -> str:
        body = {
            "seq": self._seq,
            "ts": datetime.now(UTC).isoformat(),
            "prev_hash": self._prev,
            **event,
        }
        entry_hash = _digest(self._prev, body)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({**body, "hash": entry_hash}) + "\n")
        self._seq += 1
        self._prev = entry_hash
        return entry_hash


def verify(path: Path) -> bool:
    """True if every entry's hash matches its content and links to the previous entry."""
    prev = GENESIS
    for entry in _read(path):
        claimed = entry.pop("hash")
        if entry.get("prev_hash") != prev or _digest(prev, entry) != claimed:
            return False
        prev = claimed
    return True
