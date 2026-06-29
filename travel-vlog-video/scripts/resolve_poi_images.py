#!/usr/bin/env python3
"""Resolve POI image assets for travel-vlog-video manifests."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WIDTH = 1080
HEIGHT = 1920
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
TIMEOUT_SEC = 12


def slugify(text: str) -> str:
    import re

    text = text.strip().lower()
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", text)
    return text.strip("-") or "poi"


def is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def looks_like_image_path(value: str) -> bool:
    return Path(urllib.parse.urlparse(value).path).suffix.lower() in IMAGE_EXTENSIONS


def validate_manifest(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    requests = data.get("requests")
    if not isinstance(requests, list):
        raise ValueError("manifest must contain a requests array")
    valid: List[Dict[str, Any]] = []
    for index, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"request at index {index} must be an object")
        segment_id = request.get("segment_id") or request.get("id")
        if not segment_id:
            raise ValueError(f"request at index {index} is missing segment_id/id")
        request.setdefault("segment_id", segment_id)
        request.setdefault("id", segment_id)
        request.setdefault("name", segment_id)
        request.setdefault("output", f"{slugify(str(segment_id))}.png")
        request.setdefault("direct_image_candidates", [])
        request.setdefault("source_urls", {})
        valid.append(request)
    return valid


def copy_local_image(candidate: str, output_path: Path) -> Tuple[bool, str]:
    path = Path(candidate).expanduser()
    if not path.exists() or not path.is_file():
        return False, "local_file_missing"
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False, "local_file_not_supported_image_extension"
    if path.resolve() == output_path.resolve():
        return True, "already_in_place"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, output_path)
    return True, "copied_local_image"


def download_image(candidate: str, output_path: Path) -> Tuple[bool, str]:
    if not is_http_url(candidate):
        return False, "not_http_url"
    if not looks_like_image_path(candidate):
        return False, "url_not_direct_image_candidate"
    request = urllib.request.Request(candidate, headers={"User-Agent": "OpenClaw travel-vlog-video/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEC) as response:
            content_type = response.headers.get("content-type", "").lower()
            if "image" not in content_type:
                return False, f"invalid_content_type:{content_type or 'unknown'}"
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(data) > MAX_DOWNLOAD_BYTES:
                return False, "image_too_large"
    except urllib.error.URLError as exc:
        return False, f"download_failed:{exc.reason}"
    except Exception as exc:
        return False, f"download_failed:{exc}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return True, "downloaded_direct_image"


def color_for_text(text: str) -> Tuple[int, int, int]:
    seed = sum(ord(ch) for ch in text)
    return 50 + seed % 120, 70 + (seed * 3) % 110, 120 + (seed * 5) % 100


def write_ppm_card(request: Dict[str, Any], ppm_path: Path) -> None:
    name = str(request.get("name") or request.get("segment_id") or "POI")
    city = str(request.get("city") or "Travel")
    item_type = str(request.get("type") or "poi")
    base_r, base_g, base_b = color_for_text(name + city)
    stripe_r, stripe_g, stripe_b = min(base_r + 55, 255), min(base_g + 45, 255), min(base_b + 35, 255)

    header = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii")
    with ppm_path.open("wb") as handle:
        handle.write(header)
        for y in range(HEIGHT):
            ratio = y / max(HEIGHT - 1, 1)
            r = int(base_r * (1 - ratio) + 22 * ratio)
            g = int(base_g * (1 - ratio) + 28 * ratio)
            b = int(base_b * (1 - ratio) + 50 * ratio)
            row = bytearray()
            for x in range(WIDTH):
                in_card = 110 < x < WIDTH - 110 and 520 < y < 1390
                in_top_stripe = 110 < x < WIDTH - 110 and 520 < y < 700
                in_bottom_stripe = 110 < x < WIDTH - 110 and 1260 < y < 1390
                in_accent = (x + y) % 170 < 5
                if in_top_stripe or in_bottom_stripe:
                    pixel = (stripe_r, stripe_g, stripe_b)
                elif in_card:
                    pixel = (245, 242, 232)
                elif in_accent:
                    pixel = (min(r + 35, 255), min(g + 35, 255), min(b + 35, 255))
                else:
                    pixel = (r, g, b)
                row.extend(pixel)
            handle.write(row)

    sidecar = ppm_path.with_suffix(".txt")
    source_urls = request.get("source_urls") if isinstance(request.get("source_urls"), dict) else {}
    sidecar.write_text(
        "\n".join([
            f"POI: {name}",
            f"City: {city}",
            f"Type: {item_type}",
            "Visual: fallback non-black source card",
            f"Baidu image: {source_urls.get('baidu_image', '')}",
            f"Baidu web: {source_urls.get('baidu_web', '')}",
            f"XHS: {source_urls.get('xhs', '')}",
            f"Dianping: {source_urls.get('dianping', '')}",
            f"Image search: {source_urls.get('image_search', '')}",
            f"Wikimedia: {source_urls.get('wikimedia', '')}",
            f"Official or encyclopedia: {source_urls.get('official_or_encyclopedia', '')}",
            str(request.get("source_note") or "第三方图片/平台入口仅作素材参考；下载和发布前需确认授权。"),
        ]),
        encoding="utf-8",
    )


def convert_ppm_to_png(ppm_path: Path, output_path: Path) -> Tuple[bool, str]:
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(ppm_path), str(output_path)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True, "generated_source_card"
    except FileNotFoundError:
        return False, "ffmpeg_missing"
    except subprocess.CalledProcessError as exc:
        return False, f"ffmpeg_convert_failed:{exc.stderr.strip()}"


def generate_fallback_card(request: Dict[str, Any], output_path: Path) -> Tuple[bool, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ppm_path = Path(tmp) / f"{slugify(str(request.get('segment_id')))}.ppm"
        write_ppm_card(request, ppm_path)
        ok, reason = convert_ppm_to_png(ppm_path, output_path)
        if ok:
            sidecar = ppm_path.with_suffix(".txt")
            if sidecar.exists():
                shutil.copy2(sidecar, output_path.with_suffix(".txt"))
            return True, reason
        fallback_ppm = output_path.with_suffix(".ppm")
        shutil.copy2(ppm_path, fallback_ppm)
        sidecar = ppm_path.with_suffix(".txt")
        if sidecar.exists():
            shutil.copy2(sidecar, fallback_ppm.with_suffix(".txt"))
        return True, f"generated_source_card_ppm:{reason}"


def resolve_request(request: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    output_name = str(request.get("output") or f"{slugify(str(request['segment_id']))}.png")
    if Path(output_name).suffix.lower() not in IMAGE_EXTENSIONS:
        output_name = f"{Path(output_name).stem}.png"
    output_path = out_dir / output_name
    attempts: List[Dict[str, str]] = []

    candidates = request.get("direct_image_candidates") or []
    if not isinstance(candidates, list):
        candidates = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        candidate = candidate.strip()
        if is_http_url(candidate):
            ok, reason = download_image(candidate, output_path)
        else:
            ok, reason = copy_local_image(candidate, output_path)
        attempts.append({"candidate": candidate, "result": reason})
        if ok:
            return {
                "segment_id": request["segment_id"],
                "path": str(output_path.resolve()),
                "type": "image",
                "source_type": "direct_image" if is_http_url(candidate) else "local_image",
                "source": candidate,
                "source_urls": request.get("source_urls", {}),
                "authorized_for_publish": False,
                "note": "已使用候选图片；发布前仍需确认图片授权。",
                "attempts": attempts,
            }

    ok, reason = generate_fallback_card(request, output_path)
    path = output_path if output_path.exists() else output_path.with_suffix(".ppm")
    return {
        "segment_id": request["segment_id"],
        "path": str(path.resolve()),
        "type": "image",
        "source_type": "source_card",
        "source": None,
        "source_urls": request.get("source_urls", {}),
        "authorized_for_publish": False,
        "note": "未获取可直接下载图片，已生成非黑色参考卡片。",
        "attempts": attempts + [{"candidate": "fallback_card", "result": reason if ok else "fallback_failed"}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve POI image assets for travel-vlog-video")
    parser.add_argument("--manifest", required=True, help="Path to poi_image_requests.json")
    parser.add_argument("--out-dir", required=True, help="Directory for resolved image assets")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_dir = Path(args.out_dir)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        requests = validate_manifest(data)
        out_dir.mkdir(parents=True, exist_ok=True)
        assets = [resolve_request(request, out_dir) for request in requests]
        degraded = any(asset.get("source_type") == "source_card" for asset in assets)
        warnings = []
        if degraded:
            warnings.append("部分 POI 未获取可直接下载图片，已使用非黑色参考卡片。")
        result = {"assets": assets, "degraded": degraded, "warnings": warnings}
        assets_path = out_dir.parent / "poi_image_assets.json"
        report_path = out_dir.parent / "poi_image_resolution_report.json"
        assets_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"outputs": {"poi_image_assets": str(assets_path.resolve()), "poi_image_resolution_report": str(report_path.resolve())}, **result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"degraded": True, "error_code": "fatal", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
