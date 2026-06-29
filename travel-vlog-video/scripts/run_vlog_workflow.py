#!/usr/bin/env python3
"""Run the travel-vlog-video workflow with retryable route/image/compose steps."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path("/Users/user/.openclaw")
TRAVEL_SKILL = ROOT / "skills/travel-vlog-video"
AMAP_SKILL = ROOT / "skills/amap-route-video"
COMPOSE_SCRIPT = ROOT / "skills/ffmpeg-media-compose/scripts/compose_media.py"
AMAP_OUTPUT = AMAP_SKILL / "out/amap-segmented-route.mp4"
AMAP_SPEC = AMAP_SKILL / "out/route-spec.json"

RETRYABLE_PATTERNS = [
    "timeout",
    "timed out",
    "handshake",
    "econnreset",
    "econnrefused",
    "enotfound",
    "network",
    "qps",
    "too many requests",
    "engine_response_data_error",
    "5xx",
    " 500",
    " 502",
    " 503",
    " 504",
    "remotion",
    "browser",
    "chrome",
]

NON_RETRYABLE_PATTERNS = [
    "缺少 amap_key",
    "缺少 amap_web_service_key",
    "invalid_user_key",
    "userkey_plat_nomatch",
    "user_daily_query_over_limit",
    "invalid route input",
    "missing from",
    "missing to",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return f"{key[:6]}…{key[-4:]}"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_retryable(text: str) -> Tuple[bool, str]:
    lowered = text.lower()
    for pattern in NON_RETRYABLE_PATTERNS:
        if pattern in lowered:
            return False, pattern
    for pattern in RETRYABLE_PATTERNS:
        if pattern in lowered:
            return True, pattern
    return False, "unclassified_failure"


def run_command(command: List[str], cwd: Path | None = None, env: Dict[str, str] | None = None, timeout: int | None = None) -> Dict[str, Any]:
    started = time.time()
    proc = subprocess.run(command, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True, timeout=timeout, check=False)
    return {
        "command": [str(part) for part in command],
        "cwd": str(cwd) if cwd else None,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "duration_sec": round(time.time() - started, 3),
        "ok": proc.returncode == 0,
    }


def retry_step(name: str, attempts: int, delays: List[int], fn) -> Dict[str, Any]:
    result: Dict[str, Any] = {"name": name, "attempts": [], "ok": False, "retryable": False}
    for index in range(1, max(attempts, 1) + 1):
        attempt = fn(index)
        attempt["attempt"] = index
        result["attempts"].append(attempt)
        if attempt.get("ok"):
            result["ok"] = True
            result["retryable"] = False
            return result
        combined = f"{attempt.get('stdout', '')}\n{attempt.get('stderr', '')}\n{attempt.get('error', '')}"
        retryable, reason = classify_retryable(combined)
        attempt["retryable"] = retryable
        attempt["failure_class"] = reason
        result["retryable"] = retryable
        result["failure_class"] = reason
        if not retryable or index >= attempts:
            return result
        time.sleep(delays[min(index - 1, len(delays) - 1)])
    return result


def build_plan(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    command = [sys.executable, str(TRAVEL_SKILL / "scripts/build_vlog_plan.py"), "--out-dir", str(out_dir)]
    if args.input_file:
        command.extend(["--input-file", args.input_file])
    else:
        command.extend(["--plan", args.plan])
    return run_command(command, cwd=TRAVEL_SKILL)


def enrich_and_resolve(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    def once(_: int) -> Dict[str, Any]:
        enrich = run_command([
            sys.executable,
            str(TRAVEL_SKILL / "scripts/enrich_poi_images_with_collector.py"),
            "--manifest", str(out_dir / "poi_image_requests.json"),
            "--out-manifest", str(out_dir / "poi_image_requests.enriched.json"),
            "--out-collection", str(out_dir / "poi_image_collection.json"),
            "--max-images-per-poi", str(args.max_images_per_poi),
        ], cwd=TRAVEL_SKILL, timeout=180)
        if not enrich["ok"]:
            return enrich
        resolve = run_command([
            sys.executable,
            str(TRAVEL_SKILL / "scripts/resolve_poi_images.py"),
            "--manifest", str(out_dir / "poi_image_requests.enriched.json"),
            "--out-dir", str(out_dir / "assets"),
        ], cwd=TRAVEL_SKILL, timeout=180)
        resolve["enrich"] = enrich
        return resolve
    return retry_step("image_enrich_and_resolve", args.image_retries, [1, 3, 8], once)


def route_plan_file(out_dir: Path, route: Dict[str, Any]) -> Path:
    return out_dir / "route-plans" / f"{route['id']}.json"


def generate_route(args: argparse.Namespace, out_dir: Path, route: Dict[str, Any]) -> Dict[str, Any]:
    route_id = str(route.get("id") or "route")
    report: Dict[str, Any] = {"id": route_id, "ok": False, "attempts": []}
    if not route.get("segments"):
        report.update({"retryable": False, "failure_class": "invalid route input", "error": "missing segments"})
        return report

    plan_path = route_plan_file(out_dir, route)
    write_json(plan_path, {"title": route.get("title") or route_id, "city": route.get("city") or "", "segments": route.get("segments") or []})
    route_videos = out_dir / "route-videos"
    route_specs = out_dir / "route-specs"
    route_videos.mkdir(parents=True, exist_ok=True)
    route_specs.mkdir(parents=True, exist_ok=True)
    target_video = route_videos / f"{route_id}.mp4"
    target_spec = route_specs / f"{route_id}.json"

    env = os.environ.copy()
    env["AMAP_KEY"] = args.amap_key or env.get("AMAP_KEY", "")
    env["AMAP_WEB_SERVICE_KEY"] = args.amap_key or env.get("AMAP_WEB_SERVICE_KEY", "")

    def once(attempt_index: int) -> Dict[str, Any]:
        spec = run_command(["node", "scripts/generate-route-video.mjs", "--input-file", str(plan_path), "--spec-only"], cwd=AMAP_SKILL, env=env, timeout=120)
        item: Dict[str, Any] = {"spec_only": spec, "ok": False}
        if not spec["ok"]:
            item.update({"stdout": spec.get("stdout", ""), "stderr": spec.get("stderr", "")})
            return item
        if AMAP_SPEC.exists():
            shutil.copy2(AMAP_SPEC, target_spec)
        render_input = target_spec if target_spec.exists() else plan_path
        render = run_command(["node", "scripts/generate-route-video.mjs", "--input-file", str(render_input)], cwd=AMAP_SKILL, env=env, timeout=300)
        item["render"] = render
        item.update({"stdout": render.get("stdout", ""), "stderr": render.get("stderr", "")})
        if render["ok"] and AMAP_OUTPUT.exists():
            shutil.copy2(AMAP_OUTPUT, target_video)
            item["ok"] = target_video.exists()
            item["output"] = str(target_video.resolve())
            item["route_spec"] = str(target_spec.resolve()) if target_spec.exists() else None
        return item

    step = retry_step(route_id, args.route_retries, [1, 3, 8], once)
    report.update(step)
    report["output"] = str(target_video.resolve()) if target_video.exists() else None
    report["route_spec"] = str(target_spec.resolve()) if target_spec.exists() else None
    return report


def generate_routes(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    plan = read_json(out_dir / "amap_route_plan.json")
    routes = plan.get("routes") if isinstance(plan.get("routes"), list) else []
    reports = []
    # Keep AMap route generation serial to avoid QPS errors from geocoding and route-planning APIs.
    for route in routes:
        if isinstance(route, dict):
            reports.append(generate_route(args, out_dir, route))
    result = {
        "generated_at": now(),
        "amap_key": mask_key(args.amap_key),
        "routes_total": len(routes),
        "routes_ok": sum(1 for route in reports if route.get("ok")),
        "routes_failed": sum(1 for route in reports if not route.get("ok")),
        "routes": reports,
    }
    write_json(out_dir / "route_generation_report.json", result)
    return result


def load_assets_by_segment(out_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = out_dir / "poi_image_assets.json"
    if not path.exists():
        return {}
    data = read_json(path)
    assets = data.get("assets") if isinstance(data.get("assets"), list) else []
    return {str(asset.get("segment_id")): asset for asset in assets if isinstance(asset, dict) and asset.get("segment_id")}


def build_final_manifest(out_dir: Path) -> Dict[str, Any]:
    draft = read_json(out_dir / "ffmpeg_manifest.draft.json")
    assets = load_assets_by_segment(out_dir)
    generated_items: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    title_path = out_dir / "assets/title-001.png"

    for item in draft.get("items") or []:
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path") or "")
        if not path_value.startswith("PLACEHOLDER/"):
            if Path(path_value).exists():
                generated_items.append(item)
            else:
                skipped.append({"item": item, "reason": "missing_existing_path"})
            continue
        name = Path(path_value).name
        stem = Path(name).stem
        new_item = dict(item)
        if name == "title-001.png":
            if title_path.exists():
                new_item["path"] = str(title_path.resolve())
                generated_items.append(new_item)
            else:
                skipped.append({"item": item, "reason": "missing_title_asset"})
        elif name.endswith(".mp4"):
            route_video = out_dir / "route-videos" / name
            if route_video.exists():
                new_item["path"] = str(route_video.resolve())
                generated_items.append(new_item)
            else:
                generated_items.append(new_item)
                skipped.append({"item": item, "reason": "missing_route_video"})
        elif name.endswith(".png"):
            asset = assets.get(stem)
            if asset and asset.get("path") and Path(str(asset["path"])).exists():
                new_item["path"] = str(Path(str(asset["path"])).resolve())
                new_item["segment_id"] = stem
                generated_items.append(new_item)
            else:
                skipped.append({"item": item, "reason": "missing_poi_asset"})
        else:
            skipped.append({"item": item, "reason": "unknown_placeholder"})

    manifest = dict(draft)
    manifest["output"] = args_output_name(out_dir)
    manifest["items"] = generated_items
    manifest["generated_manifest_skipped_items"] = skipped
    write_json(out_dir / "final_ffmpeg_manifest.generated.json", manifest)
    return {"manifest": manifest, "skipped_items": skipped}


def args_output_name(out_dir: Path) -> str:
    return f"{out_dir.name}-vlog.mp4"


def finalize_manifest(out_dir: Path) -> Dict[str, Any]:
    result = run_command([
        sys.executable,
        str(TRAVEL_SKILL / "scripts/finalize_ffmpeg_manifest.py"),
        "--manifest", str(out_dir / "final_ffmpeg_manifest.generated.json"),
        "--poi-assets", str(out_dir / "poi_image_assets.json"),
        "--out-manifest", str(out_dir / "final_ffmpeg_manifest.filtered.json"),
        "--out-report", str(out_dir / "final_ffmpeg_manifest.report.json"),
    ], cwd=TRAVEL_SKILL)
    return result


def compose_final(args: argparse.Namespace, out_dir: Path) -> Dict[str, Any]:
    filtered = out_dir / "final_ffmpeg_manifest.filtered.json"
    if not filtered.exists():
        return {"ok": False, "error": "filtered_manifest_missing", "retryable": False}
    data = read_json(filtered)
    if not data.get("items"):
        return {"ok": False, "error": "no_composable_items", "retryable": False}

    def once(_: int) -> Dict[str, Any]:
        return run_command([sys.executable, str(COMPOSE_SCRIPT), "--manifest", str(filtered), "--out-dir", str(out_dir / "final")], cwd=ROOT, timeout=600)
    return retry_step("compose", args.compose_retries, [1, 3, 8], once)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retryable travel vlog workflow")
    parser.add_argument("--plan", help="Natural language travel plan")
    parser.add_argument("--input-file", help="JSON travel plan file")
    parser.add_argument("--out-dir", required=True, help="Output working directory")
    parser.add_argument("--amap-key", default=os.environ.get("AMAP_KEY") or os.environ.get("AMAP_WEB_SERVICE_KEY") or "", help="AMap Web Service key")
    parser.add_argument("--route-retries", type=int, default=3)
    parser.add_argument("--image-retries", type=int, default=2)
    parser.add_argument("--compose-retries", type=int, default=2)
    parser.add_argument("--max-images-per-poi", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    report: Dict[str, Any] = {
        "started_at": now(),
        "out_dir": str(out_dir),
        "amap_key": mask_key(args.amap_key),
        "steps": {},
        "retry_policy": {
            "retryable": RETRYABLE_PATTERNS,
            "non_retryable": NON_RETRYABLE_PATTERNS,
            "backoff_seconds": [1, 3, 8],
        },
    }

    if not args.plan and not args.input_file:
        report.update({"ok": False, "error": "provide --plan or --input-file"})
        write_json(out_dir / "workflow_report.json", report)
        return 2
    if not args.amap_key:
        report.update({"ok": False, "error": "missing_amap_key"})
        write_json(out_dir / "workflow_report.json", report)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    build = build_plan(args, out_dir)
    report["steps"]["build_plan"] = build
    if not build["ok"]:
        report.update({"ok": False, "finished_at": now(), "failure_step": "build_plan"})
        write_json(out_dir / "workflow_report.json", report)
        return 1

    images = enrich_and_resolve(args, out_dir)
    report["steps"]["images"] = images

    routes = generate_routes(args, out_dir)
    report["steps"]["routes"] = routes

    generated = build_final_manifest(out_dir)
    report["steps"]["generated_manifest"] = generated
    finalize = finalize_manifest(out_dir)
    report["steps"]["finalize"] = finalize
    if not finalize["ok"]:
        report.update({"ok": False, "finished_at": now(), "failure_step": "finalize"})
        write_json(out_dir / "workflow_report.json", report)
        return 1

    compose = compose_final(args, out_dir)
    report["steps"]["compose"] = compose
    final_mp4 = out_dir / "final" / args_output_name(out_dir)
    report["final_mp4"] = str(final_mp4.resolve()) if final_mp4.exists() else None
    report["ok"] = bool(final_mp4.exists() and compose.get("ok"))
    report["finished_at"] = now()
    write_json(out_dir / "workflow_report.json", report)
    print(json.dumps({"ok": report["ok"], "final_mp4": report["final_mp4"], "workflow_report": str((out_dir / "workflow_report.json").resolve())}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
