#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def _parse_simple(frontmatter_text: str) -> tuple[dict[str, str] | None, str | None]:
    parsed: dict[str, str] = {}
    for idx, raw_line in enumerate(frontmatter_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or raw_line.startswith(" "):
            continue
        if ":" not in raw_line:
            return None, f"Invalid frontmatter line {idx}: missing ':'"
        key, value = raw_line.split(":", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parsed, None


def validate_skill(skill_path: str | Path) -> tuple[bool, str]:
    skill_path = Path(skill_path)
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid or missing YAML frontmatter"
    frontmatter_text = match.group(1)
    if yaml is not None:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except Exception as exc:
            return False, f"Invalid YAML: {exc}"
    else:
        frontmatter, error = _parse_simple(frontmatter_text)
        if error:
            return False, error
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a map"
    for key in ("name", "description"):
        if key not in frontmatter:
            return False, f"Missing {key}"
    name = str(frontmatter["name"])
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name must be kebab-case: {name}"
    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        raise SystemExit(1)
    ok, message = validate_skill(sys.argv[1])
    print(message)
    raise SystemExit(0 if ok else 1)
