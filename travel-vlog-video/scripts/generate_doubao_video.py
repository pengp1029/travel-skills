#!/usr/bin/env python3
"""Generate Doubao/Seedance videos for travel vlog segments.

Supports single-request mode, manifest batch mode, and dry-run output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = "doubao-seedance-2-0-260128"
TERMINAL_FAILURES = {"failed", "expired", "cancelled"}


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


def bool_arg(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean: {value}")


def write_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def get_api_key() -> Optional[str]:
    return os.environ.get("ARK_API_KEY") or os.environ.get("DOUBAO_API_KEY")


def build_content(prompt: str, image_url: Optional[str], image_role: str) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = []
    if prompt:
        content.append({"type": "text", "text": prompt})
    if image_url:
        item: Dict[str, Any] = {"type": "image_url", "image_url": {"url": image_url}}
        if image_role:
            item["role"] = image_role
        content.append(item)
    return content


def build_request(req: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    prompt = req.get("prompt") or defaults.get("prompt") or ""
    image_url = req.get("image_url") or defaults.get("image_url")
    image_role = req.get("image_role") or defaults.get("image_role") or "first_frame"
    content = req.get("content") or build_content(prompt, image_url, image_role)

    payload: Dict[str, Any] = {
        "model": req.get("model") or defaults.get("model") or DEFAULT_MODEL,
        "content": content,
        "resolution": req.get("resolution") or defaults.get("resolution") or "720p",
        "ratio": req.get("ratio") or defaults.get("ratio") or "9:16",
        "duration": int(req.get("duration") or defaults.get("duration") or 5),
        "watermark": bool_arg(req.get("watermark", defaults.get("watermark", False))),
        "return_last_frame": bool_arg(req.get("return_last_frame", defaults.get("return_last_frame", True))),
    }
    if req.get("seed") is not None:
        payload["seed"] = int(req["seed"])
    if req.get("callback_url"):
        payload["callback_url"] = req["callback_url"]
    if req.get("service_tier"):
        payload["service_tier"] = req["service_tier"]
    return payload


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    defaults = {
        "model": data.get("model", DEFAULT_MODEL),
        "ratio": data.get("ratio", "9:16"),
        "resolution": data.get("resolution", "720p"),
        "duration": data.get("duration", 5),
        "watermark": data.get("watermark", False),
        "return_last_frame": data.get("return_last_frame", True),
    }
    requests = data.get("requests")
    if not isinstance(requests, list):
        raise ValueError("manifest must contain requests[]")
    normalized = []
    for index, req in enumerate(requests):
        item = dict(req)
        item.setdefault("id", f"request-{index + 1:03d}")
        item["payload"] = build_request(item, defaults)
        normalized.append(item)
    return normalized


def import_ark_client(api_key: str):
    try:
        from volcenginesdkarkruntime import Ark  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "missing_sdk: install with `pip install 'volcengine-python-sdk[ark]'`"
        ) from exc

    base_url = os.environ.get("ARK_BASE_URL")
    if base_url:
        return Ark(api_key=api_key, base_url=base_url)
    return Ark(api_key=api_key)


def read_attr_or_key(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def content_value(result: Any, name: str) -> Any:
    content = read_attr_or_key(result, "content")
    if content is None:
        return None
    return read_attr_or_key(content, name)


def download_url(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            output.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"download_failed: {exc}") from exc


def run_request(client: Any, request_id: str, payload: Dict[str, Any], output: Path, poll_interval: int, timeout: int) -> Dict[str, Any]:
    create_result = client.content_generation.tasks.create(**payload)
    task_id = read_attr_or_key(create_result, "id")
    if not task_id:
        raise RuntimeError("create_task_missing_id")

    deadline = time.time() + timeout
    last_status = "unknown"
    while time.time() < deadline:
        get_result = client.content_generation.tasks.get(task_id=task_id)
        status = read_attr_or_key(get_result, "status", "unknown")
        last_status = status
        if status == "succeeded":
            video_url = content_value(get_result, "video_url")
            last_frame_url = content_value(get_result, "last_frame_url")
            if not video_url:
                return {
                    "id": request_id,
                    "task_id": task_id,
                    "status": status,
                    "degraded": True,
                    "error_code": "missing_video_url",
                }
            download_url(video_url, output)
            return {
                "id": request_id,
                "task_id": task_id,
                "status": status,
                "path": str(output.resolve()),
                "last_frame_url": last_frame_url,
                "degraded": False,
            }
        if status in TERMINAL_FAILURES:
            return {
                "id": request_id,
                "task_id": task_id,
                "status": status,
                "degraded": True,
                "error_code": "task_failed",
                "raw": str(get_result),
            }
        time.sleep(poll_interval)

    return {
        "id": request_id,
        "task_id": task_id,
        "status": last_status,
        "degraded": True,
        "error_code": "timeout",
    }


def request_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    output = args.output or "doubao-video.mp4"
    req: Dict[str, Any] = {
        "id": args.id or Path(output).stem,
        "prompt": args.prompt or "",
        "image_url": args.image_url,
        "image_role": args.image_role,
        "model": args.model,
        "ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
        "watermark": args.watermark,
        "return_last_frame": args.return_last_frame,
        "output": output,
    }
    if args.seed is not None:
        req["seed"] = args.seed
    req["payload"] = build_request(req, {})
    return req


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Doubao/Seedance travel vlog clips")
    parser.add_argument("--manifest", help="Batch manifest JSON path")
    parser.add_argument("--out-dir", default="out/doubao", help="Output directory for batch mode")
    parser.add_argument("--id", help="Request id for single mode")
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--image-url", help="Image URL, base64 data URL, or approved asset id")
    parser.add_argument("--image-role", default="first_frame", help="Image role, usually first_frame")
    parser.add_argument("--output", help="Output MP4 path for single mode")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ratio", default="9:16")
    parser.add_argument("--resolution", default="720p")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--watermark", type=bool_arg, default=False)
    parser.add_argument("--return-last-frame", type=bool_arg, default=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.manifest:
            requests = load_manifest(Path(args.manifest))
            out_dir = Path(args.out_dir)
            for req in requests:
                req.setdefault("output", f"{req['id']}.mp4")
        else:
            requests = [request_from_args(args)]
            out_dir = Path(args.out_dir)

        if args.dry_run:
            write_json({"degraded": False, "dry_run": True, "requests": requests})
            return 0

        api_key = get_api_key()
        if not api_key:
            write_json({
                "degraded": True,
                "error_code": "missing_api_key",
                "message": "Set ARK_API_KEY or DOUBAO_API_KEY, or run with --dry-run.",
                "requests": requests,
            })
            return 2

        client = import_ark_client(api_key)
        results = []
        degraded = False
        for req in requests:
            output_value = req.get("output") or f"{req['id']}.mp4"
            output_path = Path(output_value)
            if not output_path.is_absolute():
                output_path = out_dir / output_path
            try:
                result = run_request(
                    client=client,
                    request_id=req["id"],
                    payload=req["payload"],
                    output=output_path,
                    poll_interval=args.poll_interval,
                    timeout=args.timeout,
                )
            except Exception as exc:  # keep batch mode progressing
                result = {
                    "id": req["id"],
                    "degraded": True,
                    "error_code": "exception",
                    "message": str(exc),
                }
            degraded = degraded or bool(result.get("degraded"))
            results.append(result)

        write_json({"degraded": degraded, "results": results})
        return 1 if degraded else 0
    except Exception as exc:
        write_json({"degraded": True, "error_code": "fatal", "message": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
