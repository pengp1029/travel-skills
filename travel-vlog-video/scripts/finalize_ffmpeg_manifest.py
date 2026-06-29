#!/usr/bin/env python3
"""Finalize FFmpeg manifest by skipping POI images without real assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

REAL_IMAGE_SOURCE_TYPES = {"local_image", "direct_image"}
SOURCE_CARD_TYPES = {"source_card", "fallback_card", "fallback_card_for_invalid_public_image"}


def read_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def normalize_path(value: str) -> str:
    try:
        return str(Path(value).expanduser().resolve())
    except Exception:
        return value


def load_poi_assets(path: Path) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    data = read_json(path)
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("poi assets file must contain assets array")
    by_segment: Dict[str, Dict[str, Any]] = {}
    by_path: Dict[str, Dict[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        segment_id = str(asset.get("segment_id") or "").strip()
        path_value = str(asset.get("path") or "").strip()
        if segment_id:
            by_segment[segment_id] = asset
        if path_value:
            by_path[normalize_path(path_value)] = asset
    return by_segment, by_path


def infer_segment_id_from_path(path_value: str) -> str | None:
    if not path_value:
        return None
    stem = Path(path_value).stem
    return stem or None


def is_poi_image_item(item: Dict[str, Any], assets_by_path: Dict[str, Dict[str, Any]], assets_by_segment: Dict[str, Dict[str, Any]]) -> tuple[bool, Dict[str, Any] | None]:
    path_value = str(item.get("path") or "").strip()
    if path_value:
        asset = assets_by_path.get(normalize_path(path_value))
        if asset:
            return True, asset
    segment_id = str(item.get("segment_id") or item.get("id") or "").strip()
    if segment_id and segment_id in assets_by_segment:
        return True, assets_by_segment[segment_id]
    inferred = infer_segment_id_from_path(path_value)
    if inferred and inferred in assets_by_segment:
        return True, assets_by_segment[inferred]
    if inferred and inferred.startswith("poi-"):
        return True, None
    return False, None


def is_real_poi_image(asset: Dict[str, Any] | None, include_source_cards: bool) -> bool:
    if not asset:
        return False
    source_type = str(asset.get("source_type") or "").strip()
    if source_type in REAL_IMAGE_SOURCE_TYPES:
        return True
    if include_source_cards and source_type in SOURCE_CARD_TYPES:
        return True
    return False


def file_exists_for_item(item: Dict[str, Any]) -> bool:
    path_value = str(item.get("path") or "").strip()
    if not path_value:
        return False
    if path_value.startswith("PLACEHOLDER/"):
        return False
    return Path(path_value).expanduser().exists()


def is_route_video_item(item: Dict[str, Any]) -> bool:
    path_value = str(item.get("path") or "").strip()
    if path_value.startswith("PLACEHOLDER/route-") and path_value.endswith(".mp4"):
        return True
    return Path(path_value).name.startswith("route-") and path_value.endswith(".mp4")


def filter_items(
    manifest: Dict[str, Any],
    assets_by_segment: Dict[str, Dict[str, Any]],
    assets_by_path: Dict[str, Dict[str, Any]],
    include_source_cards: bool,
    drop_orphan_arrival_images: bool,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest must contain items array")

    kept_items: List[Dict[str, Any]] = []
    kept_poi_images: List[Dict[str, Any]] = []
    skipped_poi_images: List[Dict[str, Any]] = []
    missing_items: List[Dict[str, Any]] = []
    seen_poi_segments: set[str] = set()
    skip_next_arrival_image = False

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path") or "").strip()
        is_poi, asset = is_poi_image_item(item, assets_by_path, assets_by_segment)
        if is_poi:
            segment_id = str((asset or {}).get("segment_id") or infer_segment_id_from_path(path_value) or item.get("segment_id") or "").strip()
            if segment_id:
                seen_poi_segments.add(segment_id)
            source_type = str((asset or {}).get("source_type") or "missing_poi_asset").strip()
            if skip_next_arrival_image and drop_orphan_arrival_images:
                skipped_poi_images.append({
                    "index": index,
                    "segment_id": segment_id,
                    "source_type": source_type,
                    "path": path_value,
                    "reason": "orphan_arrival_image_after_missing_route",
                    "source_urls": (asset or {}).get("source_urls", {}),
                })
                skip_next_arrival_image = False
                continue
            skip_next_arrival_image = False
            if is_real_poi_image(asset, include_source_cards):
                if file_exists_for_item(item):
                    kept_items.append(item)
                    kept_poi_images.append({"index": index, "segment_id": segment_id, "source_type": source_type, "path": path_value})
                else:
                    missing_items.append({"index": index, "path": path_value, "reason": "file_missing", "segment_id": segment_id})
            else:
                skipped_poi_images.append({
                    "index": index,
                    "segment_id": segment_id,
                    "source_type": source_type,
                    "path": path_value,
                    "reason": "no_acquired_real_image",
                    "source_urls": (asset or {}).get("source_urls", {}),
                })
            continue

        if file_exists_for_item(item):
            kept_items.append(item)
            skip_next_arrival_image = False
        else:
            reason = "missing_route_video" if is_route_video_item(item) else "file_missing"
            missing_items.append({"index": index, "path": path_value, "reason": reason})
            skip_next_arrival_image = reason == "missing_route_video"

    for segment_id, asset in assets_by_segment.items():
        if segment_id in seen_poi_segments:
            continue
        source_type = str(asset.get("source_type") or "").strip()
        if not is_real_poi_image(asset, include_source_cards):
            skipped_poi_images.append({
                "index": None,
                "segment_id": segment_id,
                "source_type": source_type,
                "path": str(asset.get("path") or ""),
                "reason": "no_acquired_real_image_not_referenced_in_manifest",
                "source_urls": asset.get("source_urls", {}),
            })

    report = {
        "items_before": len(items),
        "items_after": len(kept_items),
        "include_source_cards": include_source_cards,
        "drop_orphan_arrival_images": drop_orphan_arrival_images,
        "kept_poi_images": kept_poi_images,
        "skipped_poi_images": skipped_poi_images,
        "missing_items": missing_items,
        "degraded": bool(skipped_poi_images or missing_items),
    }
    return kept_items, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter final FFmpeg manifest to skip POI source cards by default.")
    parser.add_argument("--manifest", required=True, help="Input FFmpeg manifest JSON")
    parser.add_argument("--poi-assets", required=True, help="poi_image_assets.json path")
    parser.add_argument("--out-manifest", required=True, help="Filtered output manifest path")
    parser.add_argument("--out-report", required=True, help="Filtering report path")
    parser.add_argument("--include-source-cards", action="store_true", help="Explicitly include source cards in final video")
    parser.add_argument("--keep-orphan-arrival-images", action="store_true", help="Keep destination POI images even when the immediately preceding route video is missing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    poi_assets_path = Path(args.poi_assets)
    out_manifest = Path(args.out_manifest)
    out_report = Path(args.out_report)

    manifest = read_json(manifest_path)
    assets_by_segment, assets_by_path = load_poi_assets(poi_assets_path)
    kept_items, report = filter_items(
        manifest,
        assets_by_segment,
        assets_by_path,
        args.include_source_cards,
        not args.keep_orphan_arrival_images,
    )

    result = dict(manifest)
    result["items"] = kept_items
    result["source_card_policy"] = "include_explicitly" if args.include_source_cards else "skip_missing_poi_images"
    result["orphan_arrival_image_policy"] = "keep" if args.keep_orphan_arrival_images else "drop_after_missing_route"

    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out_manifest": str(out_manifest.resolve()), "out_report": str(out_report.resolve()), **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
