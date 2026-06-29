from __future__ import annotations

import os
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TOOL_ROOT.parent
HISTORY_ROOT = SKILL_ROOT / ".history"
SNAPSHOT_ROOT = HISTORY_ROOT / "snapshots"
VERSIONS_FILE = HISTORY_ROOT / "versions.json"


def load_openclaw_env() -> None:
    for parent in Path(__file__).resolve().parents:
        if parent.name != ".openclaw":
            continue
        env_path = parent / ".env"
        if not env_path.exists():
            return
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
        return


load_openclaw_env()

AMAP_KEY = os.getenv("AMAP_KEY", "")
AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com/v3")

WEATHER_KEY = os.getenv("WEATHER_KEY", "")
WEATHER_BASE_URL = os.getenv("WEATHER_BASE_URL", "https://devapi.qweather.com/v7")

WEB_SEARCH_BASE_URL = os.getenv("WEB_SEARCH_BASE_URL", "https://api.duckduckgo.com/")

REQUEST_TIMEOUT = int(os.getenv("TRAVEL_SKILL_REQUEST_TIMEOUT", "10"))
DEFAULT_FORECAST_DAYS = 3
DEFAULT_SEARCH_RADIUS = 2000
DEFAULT_WEB_SEARCH_LIMIT = 5

TRACKED_PATHS = ["SKILL.md", "reference.md", "examples.md", "requirements.md", "scripts", "tools"]
