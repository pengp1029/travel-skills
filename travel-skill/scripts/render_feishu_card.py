from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from helper import build_feishu_channel_payload, build_feishu_fallback_text, build_feishu_recommendation_card


def load_item(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    data = json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    if isinstance(data, dict) and isinstance(data.get("pois"), list) and data["pois"]:
        data = data["pois"][0]
    if not isinstance(data, dict):
        raise ValueError("input must be a recommendation object or an object containing data.pois")
    return data


def render(item: dict[str, Any], mode: str) -> Any:
    card = item.get("feishu_card") if isinstance(item.get("feishu_card"), dict) else build_feishu_recommendation_card(item)
    if mode == "card":
        return card
    if mode == "channel-data":
        return build_feishu_channel_payload(card)
    if mode == "fallback-text":
        return build_feishu_fallback_text(item)
    raise ValueError(f"unsupported mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render travel recommendation data as Feishu card payload.")
    parser.add_argument("--input", help="JSON file path. Reads stdin when omitted.")
    parser.add_argument("--mode", choices=["card", "channel-data", "fallback-text"], default="card")
    args = parser.parse_args()

    item = load_item(args.input)
    output = render(item, args.mode)
    if isinstance(output, str):
        print(output)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
