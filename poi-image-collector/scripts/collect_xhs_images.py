#!/usr/bin/env python3
"""Collect Xiaohongshu note references for POI image sourcing.

This script invokes the bundled xiaohongshu-skills CLI in read-only mode and
normalizes search results into poi-image-collector compatible JSON. It does not
publish, comment, like, favorite, bypass verification, or download images.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_XHS_SKILL_DIR = str(
    Path(os.environ.get("OPENCLAW_HOME") or (Path.home() / ".openclaw"))
    / "skills"
    / "xiaohongshu-skills"
)

DEFAULT_TIMEOUT_SEC = 45


def make_xhs_search_url(query: str) -> str:
    return f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(query)}"


def make_note_url(feed_id: str, xsec_token: str | None = None) -> str:
    base = f"https://www.xiaohongshu.com/explore/{feed_id}"
    if xsec_token:
        return f"{base}?xsec_token={urllib.parse.quote(xsec_token)}"
    return base


def first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def find_nested_string(data: Any, keys: set[str]) -> str | None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys and isinstance(value, str) and value.strip():
                return value.strip()
        for value in data.values():
            found = find_nested_string(value, keys)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_nested_string(item, keys)
            if found:
                return found
    return None


def extract_author(note_card: Dict[str, Any]) -> str | None:
    user = note_card.get("user") or note_card.get("user_info") or note_card.get("author")
    if isinstance(user, dict):
        return first_string(user.get("nickname"), user.get("name"), user.get("nick_name"))
    if isinstance(user, str):
        return user.strip() or None
    return find_nested_string(note_card, {"nickname", "nick_name", "user_name"})


def extract_cover_url(note_card: Dict[str, Any]) -> str | None:
    return first_string(
        note_card.get("cover"),
        note_card.get("cover_url"),
        note_card.get("image"),
        note_card.get("image_url"),
        note_card.get("url"),
        find_nested_string(note_card, {"cover", "cover_url", "image_url", "url"}),
    )


def normalize_feed(feed: Dict[str, Any]) -> Dict[str, Any]:
    note_card = feed.get("note_card") if isinstance(feed.get("note_card"), dict) else {}
    feed_id = first_string(feed.get("id"), feed.get("feed_id"), note_card.get("id")) or ""
    xsec_token = first_string(feed.get("xsec_token"), feed.get("xsecToken"), note_card.get("xsec_token"))
    title = first_string(note_card.get("display_title"), note_card.get("title"), feed.get("title"))
    cover_url = extract_cover_url(note_card)
    author = extract_author(note_card)
    note_url = make_note_url(feed_id, xsec_token) if feed_id else None
    return {
        "feed_id": feed_id,
        "xsec_token": xsec_token,
        "title": title,
        "author": author,
        "cover_url": cover_url,
        "note_url": note_url,
        "raw_interaction": note_card.get("interact_info") or note_card.get("interaction") or {},
        "source_note": "小红书结果仅作近期体验、氛围和图片参考；发布前需确认授权。",
    }


def run_xhs_search(xhs_skill_dir: Path, query: str, limit: int) -> tuple[int, str, str]:
    uv = shutil.which("uv")
    if uv:
        command = [uv, "run", "python", "scripts/cli.py", "search-feeds", "--keyword", query, "--note-type", "图文"]
    else:
        command = [sys.executable, "scripts/cli.py", "search-feeds", "--keyword", query, "--note-type", "图文"]

    process = subprocess.run(
        command,
        cwd=str(xhs_skill_dir),
        text=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT_SEC,
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def build_degraded(city: str, poi: str, query: str, reason: str, xhs_skill_dir: str, warnings: List[str]) -> Dict[str, Any]:
    return {
        "source": "xiaohongshu",
        "city": city,
        "poi": poi,
        "query": query,
        "xhs_skill_dir": xhs_skill_dir,
        "source_urls": {"xhs": make_xhs_search_url(query)},
        "xhs_notes": [],
        "reference_image_candidates": [],
        "degraded": True,
        "degraded_reason": reason,
        "warnings": warnings,
    }


def collect(city: str, poi: str, limit: int, xhs_skill_dir: str) -> Dict[str, Any]:
    query = " ".join(part for part in [city, poi, "拍照"] if part)
    skill_dir = Path(xhs_skill_dir).expanduser().resolve()
    cli_path = skill_dir / "scripts" / "cli.py"
    if not cli_path.exists():
        return build_degraded(city, poi, query, "xhs_cli_not_found", str(skill_dir), [f"CLI not found: {cli_path}"])

    try:
        returncode, stdout, stderr = run_xhs_search(skill_dir, query, limit)
    except subprocess.TimeoutExpired:
        return build_degraded(city, poi, query, "xhs_cli_timeout", str(skill_dir), ["Xiaohongshu CLI timed out; stop without retrying."])
    except Exception as exc:
        return build_degraded(city, poi, query, "xhs_cli_execution_failed", str(skill_dir), [str(exc)])

    if returncode != 0:
        reason = "xhs_not_logged_in_or_unavailable" if returncode == 1 else "xhs_cli_error"
        return build_degraded(city, poi, query, reason, str(skill_dir), [stderr.strip() or stdout.strip() or f"exit_code={returncode}"])

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return build_degraded(city, poi, query, "xhs_cli_invalid_json", str(skill_dir), [str(exc), stdout[:500]])

    feeds = payload.get("feeds") if isinstance(payload, dict) else []
    if not isinstance(feeds, list):
        feeds = []
    notes = [normalize_feed(feed) for feed in feeds[:limit] if isinstance(feed, dict)]
    reference_images = [
        {
            "url": note["cover_url"],
            "source": "xhs_cover",
            "note_url": note.get("note_url"),
            "authorized_for_publish": False,
            "usable_for_preview": True,
            "note": "小红书封面仅作本地预览或参考候选；发布前需确认授权。",
        }
        for note in notes
        if note.get("cover_url")
    ]
    return {
        "source": "xiaohongshu",
        "city": city,
        "poi": poi,
        "query": query,
        "xhs_skill_dir": str(skill_dir),
        "source_urls": {"xhs": make_xhs_search_url(query)},
        "xhs_notes": notes,
        "reference_image_candidates": reference_images,
        "degraded": not bool(notes),
        "degraded_reason": None if notes else "no_xhs_notes_found",
        "warnings": ["Xiaohongshu images are references only; authorized_for_publish defaults to false."],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Xiaohongshu image references for a POI.")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--poi", required=True, help="POI name")
    parser.add_argument("--limit", type=int, default=5, help="Maximum search results to normalize")
    parser.add_argument("--xhs-skill-dir", default=DEFAULT_XHS_SKILL_DIR, help="xiaohongshu-skills directory")
    parser.add_argument("--out", required=True, help="Output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = collect(args.city, args.poi, max(args.limit, 1), args.xhs_skill_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
