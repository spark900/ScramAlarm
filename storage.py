"""Simple JSON-backed alarm storage.

Alarms persist to ``$XDG_DATA_HOME/alarm-tui/alarms.json`` (falling back to
``~/.local/share/alarm-tui/alarms.json``) so they survive across TUI
sessions, CLI invocations, and the systemd-managed background session.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "alarm-tui"
ALARMS_FILE = DATA_DIR / "alarms.json"


@dataclass
class Alarm:
    id: str
    label: str
    trigger_at: str  # ISO 8601
    active: bool = True
    snooze_count: int = 0

    @property
    def trigger_datetime(self) -> datetime:
        return datetime.fromisoformat(self.trigger_at)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Alarm":
        return Alarm(
            id=data["id"],
            label=data["label"],
            trigger_at=data["trigger_at"],
            active=data.get("active", True),
            snooze_count=data.get("snooze_count", 0),
        )


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_alarms() -> List[Alarm]:
    _ensure_data_dir()
    if not ALARMS_FILE.exists():
        return []
    try:
        raw = json.loads(ALARMS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [Alarm.from_dict(item) for item in raw]


def save_alarms(alarms: List[Alarm]) -> None:
    _ensure_data_dir()
    tmp_file = ALARMS_FILE.with_suffix(".tmp")
    tmp_file.write_text(
        json.dumps([alarm.to_dict() for alarm in alarms], indent=2), encoding="utf-8"
    )
    tmp_file.replace(ALARMS_FILE)  # atomic on the same filesystem


def new_alarm(label: str, trigger_at: datetime) -> Alarm:
    return Alarm(id=uuid.uuid4().hex[:8], label=label or "Alarm", trigger_at=trigger_at.isoformat())
