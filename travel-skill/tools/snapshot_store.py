from __future__ import annotations

import json
from pathlib import Path

from config import HISTORY_ROOT, SNAPSHOT_ROOT, VERSIONS_FILE
from tool_types import SnapshotMeta


def ensure_history_dirs() -> None:
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)


def load_versions() -> list[SnapshotMeta]:
    ensure_history_dirs()
    if not VERSIONS_FILE.exists():
        return []
    raw = json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))
    return [SnapshotMeta(**item) for item in raw]


def save_versions(versions: list[SnapshotMeta]) -> None:
    ensure_history_dirs()
    VERSIONS_FILE.write_text(json.dumps([item.to_dict() for item in versions], ensure_ascii=False, indent=2), encoding="utf-8")


def snapshot_dir(version: str) -> Path:
    ensure_history_dirs()
    return SNAPSHOT_ROOT / version
