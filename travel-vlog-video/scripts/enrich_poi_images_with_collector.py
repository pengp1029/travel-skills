#!/usr/bin/env python3
"""Enrich travel-vlog-video POI image requests with poi-image-collector output.

The script preserves user-provided local images and direct image URLs first,
then appends verified public direct image candidates and source entries from
poi-image-collector. Source discovery and licensing policy stay in the collector.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

OPENCLAW_HOME = Path(os.environ.get("OPENCLAW_HOME") or (Path.home() / ".openclaw"))
DEFAULT_COLLECTOR_SCRIPT = str(OPENCLAW_HOME / "skills/poi-image-collector/scripts/build_image_requests.py")
DEFAULT_ACQUISITION_SCRIPT = str(OPENCLAW_HOME / "skills/poi-image-collector/scripts/acquire_public_images.py")
DEFAULT_XHS_SKILL_DIR = str(OPENCLAW_HOME / "skills/xiaohongshu-skills")


def dedupe_strings(values: List[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def merge_dicts_keep_existing(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for key, value in (incoming or {}).items():
        if value in (None, "", [], {}):
            continue
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
    return merged


def read_manifest(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    requests = data.get("requests")
    if not isinstance(requests, list):
        raise ValueError("manifest must contain requests array")
    return data


def poi_arg_from_request(request: Dict[str, Any]) -> str:
    name = str(request.get("name") or request.get("segment_id") or request.get("id") or "POI")
    poi_type = str(request.get("type") or "unknown")
    return f"{poi_type}:{name}"


def infer_city(requests: List[Dict[str, Any]]) -> str:
    for request in requests:
        city = request.get("city")
        if isinstance(city, str) and city.strip():
            return city.strip()
    return ""


def run_collector(
    collector_script: Path,
    city: str,
    requests: List[Dict[str, Any]],
    xhs_skill_dir: str | None,
    out_collection: Path,
) -> Dict[str, Any]:
    if not collector_script.exists():
        raise FileNotFoundError(f"collector script not found: {collector_script}")
    pois = ",".join(poi_arg_from_request(request) for request in requests)
    command = [
        sys.executable,
        str(collector_script),
        "--city",
        city,
        "--pois",
        pois,
        "--usage",
        "travel_vlog_preview",
        "--out",
        str(out_collection),
    ]
    if xhs_skill_dir:
        command.extend(["--xhs-skill-dir", xhs_skill_dir])
    subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(out_collection.read_text(encoding="utf-8"))


def run_acquisition(
    acquisition_script: Path,
    collection_path: Path,
    max_images_per_poi: int,
) -> tuple[Dict[str, Any], str | None]:
    if not acquisition_script.exists():
        return json.loads(collection_path.read_text(encoding="utf-8")), f"acquisition_script_missing:{acquisition_script}"
    command = [
        sys.executable,
        str(acquisition_script),
        "--collection",
        str(collection_path),
        "--out",
        str(collection_path),
        "--max-images-per-poi",
        str(max_images_per_poi),
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        warning = f"public_image_acquisition_failed:{process.stderr.strip() or process.stdout.strip()}"
        warnings = collection.get("warnings") if isinstance(collection.get("warnings"), list) else []
        warnings.append(warning)
        collection["warnings"] = warnings
        collection_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
        return collection, warning
    return json.loads(collection_path.read_text(encoding="utf-8")), None


def index_collection(collection: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    by_name: Dict[str, Dict[str, Any]] = {}
    pois = collection.get("pois") if isinstance(collection.get("pois"), list) else []
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        name = str(poi.get("name") or "").strip()
        if name:
            by_name[name] = poi
    return by_name


def enrich_request(request: Dict[str, Any], collector_poi: Dict[str, Any] | None) -> Dict[str, Any]:
    enriched = dict(request)
    collector_poi = collector_poi or {}

    existing_candidates = enriched.get("direct_image_candidates")
    if not isinstance(existing_candidates, list):
        existing_candidates = []
    collector_candidates: List[str] = []
    for candidate in collector_poi.get("direct_image_candidates") or []:
        if isinstance(candidate, str):
            collector_candidates.append(candidate)
        elif isinstance(candidate, dict) and isinstance(candidate.get("url"), str):
            collector_candidates.append(candidate["url"])
    enriched["direct_image_candidates"] = dedupe_strings(list(existing_candidates) + collector_candidates)

    source_urls = enriched.get("source_urls") if isinstance(enriched.get("source_urls"), dict) else {}
    collector_source_urls = collector_poi.get("source_urls") if isinstance(collector_poi.get("source_urls"), dict) else {}
    if "browser_search" in collector_source_urls and "image_search" not in collector_source_urls:
        collector_source_urls = dict(collector_source_urls)
        collector_source_urls["image_search"] = collector_source_urls["browser_search"]
    enriched["source_urls"] = merge_dicts_keep_existing(source_urls, collector_source_urls)

    for key in ["reference_image_candidates", "xhs_notes", "baidu_search_entries"]:
        existing = enriched.get(key) if isinstance(enriched.get(key), list) else []
        incoming = collector_poi.get(key) if isinstance(collector_poi.get(key), list) else []
        enriched[key] = existing + incoming

    collector_note = "已通过 poi-image-collector 补充多渠道搜索入口；第三方图片发布前需确认授权。"
    existing_note = str(enriched.get("source_note") or "").strip()
    enriched["source_note"] = f"{existing_note} {collector_note}".strip()
    return enriched


def build_enriched_manifest(manifest: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
    requests = [request for request in manifest.get("requests", []) if isinstance(request, dict)]
    by_name = index_collection(collection)
    enriched_requests = []
    for request in requests:
        name = str(request.get("name") or "").strip()
        enriched_requests.append(enrich_request(request, by_name.get(name)))
    result = dict(manifest)
    result["default_strategy"] = "prefer_user_image_then_collector_direct_image_then_source_card"
    result["collector"] = {
        "name": "poi-image-collector",
        "version": collection.get("version"),
        "xhs_enabled": collection.get("xhs_enabled"),
        "xhs_skill_dir": collection.get("xhs_skill_dir"),
        "public_image_acquisition": collection.get("public_image_acquisition"),
        "warnings": collection.get("warnings", []),
    }
    result["requests"] = enriched_requests
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich POI image requests with poi-image-collector output.")
    parser.add_argument("--manifest", required=True, help="Input travel-vlog-video poi_image_requests.json")
    parser.add_argument("--collector-script", default=DEFAULT_COLLECTOR_SCRIPT, help="poi-image-collector build_image_requests.py")
    parser.add_argument("--acquisition-script", default=DEFAULT_ACQUISITION_SCRIPT, help="Optional public image acquisition script")
    parser.add_argument("--acquire-public-images", dest="acquire_public_images", action="store_true", default=True, help="Acquire verified public direct image candidates after building the collection")
    parser.add_argument("--no-acquire-public-images", dest="acquire_public_images", action="store_false", help="Skip public direct image acquisition")
    parser.add_argument("--max-images-per-poi", type=int, default=2, help="Maximum public direct image candidates to acquire per POI")
    parser.add_argument("--xhs-skill-dir", default=DEFAULT_XHS_SKILL_DIR, help="Optional xiaohongshu-skills directory")
    parser.add_argument("--city", default=None, help="Override city")
    parser.add_argument("--out-manifest", required=True, help="Output enriched manifest path")
    parser.add_argument("--out-collection", required=True, help="Output collector collection JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    out_manifest = Path(args.out_manifest)
    out_collection = Path(args.out_collection)
    manifest = read_manifest(manifest_path)
    requests = [request for request in manifest.get("requests", []) if isinstance(request, dict)]
    city = args.city or infer_city(requests)
    if not city:
        raise ValueError("city is required; pass --city or include city in requests")

    out_collection.parent.mkdir(parents=True, exist_ok=True)
    collection = run_collector(Path(args.collector_script), city, requests, args.xhs_skill_dir, out_collection)
    acquisition_warning = None
    if args.acquire_public_images:
        collection, acquisition_warning = run_acquisition(
            Path(args.acquisition_script),
            out_collection,
            args.max_images_per_poi,
        )
    enriched = build_enriched_manifest(manifest, collection)
    if acquisition_warning:
        enriched.setdefault("collector", {}).setdefault("warnings", []).append(acquisition_warning)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"outputs": {"out_manifest": str(out_manifest.resolve()), "out_collection": str(out_collection.resolve())}, "requests": len(enriched.get("requests", []))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"degraded": True, "error_code": "fatal", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
