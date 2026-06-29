#!/usr/bin/env python3
"""Self-contained FFmpeg media compose helper.

It normalizes videos and images into same-size MP4 segments, then concatenates them.
All temporary and output files stay under the selected output/work directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


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


@dataclass
class ComposeResult:
    uri: str = ""
    path: str = ""
    width: int = 1080
    height: int = 1920
    fps: int = 30
    duration_sec: float = 0.0
    segments: list[dict[str, Any]] = field(default_factory=list)
    degraded: bool = False
    errors: list[str] = field(default_factory=list)


def run(cmd: list[str], *, timeout: float = 300.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing binary: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timeout after {timeout}s: {shlex.join(cmd)}") from exc


def require_ffmpeg() -> str:
    proc = run(["ffmpeg", "-version"], timeout=15)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg unavailable: {proc.stderr[-500:]}")
    first = (proc.stdout or proc.stderr).splitlines()[0]
    return first.strip()


def ffprobe_duration(path: Path) -> float:
    proc = run([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], timeout=30)
    if proc.returncode != 0:
        return 0.0
    try:
        return max(0.0, float(proc.stdout.strip()))
    except ValueError:
        return 0.0


def as_uri(path: Path) -> str:
    base_url = os.getenv("FFMPEG_COMPOSE_STATIC_BASE_URL", "").rstrip("/")
    static_dir = os.getenv("FFMPEG_COMPOSE_STATIC_DIR", "")
    if base_url and static_dir:
        try:
            rel = path.resolve().relative_to(Path(static_dir).resolve())
            return f"{base_url}/{rel.as_posix()}"
        except ValueError:
            pass
    return path.resolve().as_uri()


def media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTS:
        return "image"
    if suffix in VIDEO_EXTS:
        return "video"
    raise ValueError(f"unsupported media type: {path}")


def escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def normalize_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={fps},format=yuv420p,setsar=1"
    )


def render_image_segment(item: dict[str, Any], output: Path, *, width: int, height: int, fps: int, default_duration: float) -> float:
    source = Path(item["path"]).expanduser().resolve()
    duration = float(item.get("duration") or item.get("duration_sec") or default_duration)
    vf = normalize_filter(width, height, fps)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{duration:.3f}", "-i", str(source),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-movflags", "+faststart",
        str(output),
    ]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"image segment failed for {source}: {proc.stderr[-800:]}")
    return duration


def render_video_segment(item: dict[str, Any], output: Path, *, width: int, height: int, fps: int) -> float:
    source = Path(item["path"]).expanduser().resolve()
    requested = item.get("duration") or item.get("duration_sec")
    source_duration = ffprobe_duration(source)
    duration = float(requested) if requested else source_duration
    vf = normalize_filter(width, height, fps)
    cmd = ["ffmpeg", "-y"]
    start = item.get("start") or item.get("start_sec")
    if start is not None:
        cmd.extend(["-ss", str(float(start))])
    cmd.extend(["-i", str(source)])
    if requested:
        cmd.extend(["-t", f"{duration:.3f}"])
    cmd.extend([
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-movflags", "+faststart",
        str(output),
    ])
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"video segment failed for {source}: {proc.stderr[-800:]}")
    return duration


def concat_segments(segment_paths: list[Path], output: Path) -> None:
    concat_file = output.parent / "concat.txt"
    concat_file.write_text("".join(f"file '{escape_concat_path(p)}'\n" for p in segment_paths), encoding="utf-8")
    copy_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output),
    ]
    proc = run(copy_cmd)
    if proc.returncode == 0 and output.exists():
        return
    transcode_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart",
        str(output),
    ]
    proc = run(transcode_cmd)
    if proc.returncode != 0 or not output.exists():
        raise RuntimeError(f"concat failed: {proc.stderr[-1000:]}")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest_from_inputs(inputs: list[str], *, image_duration: float, output: str) -> dict[str, Any]:
    return {
        "output": output,
        "items": [{"path": item, "duration": image_duration} for item in inputs],
    }


def compose(manifest: dict[str, Any], *, out_dir: Path) -> ComposeResult:
    require_ffmpeg()
    items = manifest.get("items") or manifest.get("segments") or []
    if not items:
        raise ValueError("manifest requires non-empty items")
    width = int(manifest.get("width") or 1080)
    height = int(manifest.get("height") or 1920)
    fps = int(manifest.get("fps") or 30)
    default_image_duration = float(manifest.get("image_duration") or manifest.get("image_duration_sec") or 3.0)
    output_name = manifest.get("output") or f"compose_{int(time.time())}.mp4"
    output_path = (out_dir / output_name).resolve() if not Path(output_name).is_absolute() else Path(output_name).resolve()
    work_dir = output_path.parent / f"work_{output_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    segment_paths: list[Path] = []
    rendered: list[dict[str, Any]] = []
    total_duration = 0.0
    for index, raw in enumerate(items, start=1):
        item = dict(raw)
        source = Path(item["path"]).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"input not found: {source}")
        kind = item.get("type") or media_type(source)
        item["path"] = str(source)
        segment_path = work_dir / f"segment_{index:03d}.mp4"
        if kind == "image":
            duration = render_image_segment(item, segment_path, width=width, height=height, fps=fps, default_duration=default_image_duration)
        elif kind == "video":
            duration = render_video_segment(item, segment_path, width=width, height=height, fps=fps)
        else:
            raise ValueError(f"unsupported item type: {kind}")
        segment_paths.append(segment_path)
        total_duration += duration
        rendered.append({"index": index, "type": kind, "source": str(source), "segment": str(segment_path), "duration_sec": duration})

    concat_segments(segment_paths, output_path)
    return ComposeResult(
        uri=as_uri(output_path),
        path=str(output_path),
        width=width,
        height=height,
        fps=fps,
        duration_sec=round(total_duration, 3),
        segments=rendered,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose videos and images into one MP4 using ffmpeg")
    parser.add_argument("--manifest", help="JSON manifest path")
    parser.add_argument("--inputs", nargs="*", default=[], help="Input media paths in order")
    parser.add_argument("--output", default="composed.mp4", help="Output file name or absolute path")
    parser.add_argument("--out-dir", default="out", help="Output directory for relative output paths")
    parser.add_argument("--image-duration", type=float, default=3.0, help="Default image duration in seconds")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.manifest:
            manifest = load_manifest(Path(args.manifest).expanduser().resolve())
            manifest.setdefault("output", args.output)
            manifest.setdefault("width", args.width)
            manifest.setdefault("height", args.height)
            manifest.setdefault("fps", args.fps)
        else:
            manifest = build_manifest_from_inputs(args.inputs, image_duration=args.image_duration, output=args.output)
            manifest.update({"width": args.width, "height": args.height, "fps": args.fps})
        result = compose(manifest, out_dir=Path(args.out_dir).expanduser().resolve())
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        result = ComposeResult(degraded=True, errors=[str(error)])
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
