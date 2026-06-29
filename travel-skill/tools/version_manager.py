from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from config import SKILL_ROOT, TRACKED_PATHS
from snapshot_store import load_versions, save_versions, snapshot_dir
from tool_types import SnapshotMeta


def _next_version_id() -> str:
    return "v" + datetime.now().strftime("%Y%m%d_%H%M%S")


def _copy_path(src: Path, dest: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _resolve_paths(paths: list[str] | None = None) -> list[str]:
    selected = paths or TRACKED_PATHS
    return [rel_path for rel_path in selected if (SKILL_ROOT / rel_path).exists()]


def create_snapshot(note: str = "", paths: list[str] | None = None) -> SnapshotMeta:
    version = _next_version_id()
    version_dir = snapshot_dir(version)
    files = _resolve_paths(paths)
    for rel_path in files:
        _copy_path(SKILL_ROOT / rel_path, version_dir / rel_path)
    versions = load_versions()
    meta = SnapshotMeta.create(version=version, note=note, files=files)
    versions.append(meta)
    save_versions(versions)
    return meta


def list_snapshots() -> list[SnapshotMeta]:
    return load_versions()


def rollback_to(version_id: str, paths: list[str] | None = None) -> SnapshotMeta:
    versions = load_versions()
    matched = next((item for item in versions if item.version == version_id), None)
    if not matched:
        raise ValueError(f"未找到版本: {version_id}")
    version_dir = snapshot_dir(version_id)
    selected = _resolve_paths(paths or matched.files)
    for rel_path in selected:
        backup_source = version_dir / rel_path
        if not backup_source.exists():
            continue
        target = SKILL_ROOT / rel_path
        if target.exists() and target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        _copy_path(backup_source, target)
    return matched
