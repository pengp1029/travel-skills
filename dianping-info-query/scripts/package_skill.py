#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from quick_validate import validate_skill


def package_skill(skill_path: str | Path, output_dir: str | Path | None = None) -> Path | None:
    skill_path = Path(skill_path).resolve()
    ok, message = validate_skill(skill_path)
    if not ok:
        print(f"Validation failed: {message}")
        return None
    output = Path(output_dir).resolve() if output_dir else Path.cwd() / "output"
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{skill_path.name}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_path.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(skill_path.parent))
    print(target)
    return target


if __name__ == "__main__":
    if len(sys.argv) not in {2, 3}:
        print("Usage: python package_skill.py <skill_path> [output_dir]")
        raise SystemExit(1)
    result = package_skill(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    raise SystemExit(0 if result else 1)
