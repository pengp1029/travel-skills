---
name: ffmpeg-media-compose
description: >
  基于 FFmpeg 的视频和图片拼接 skill。用户想把多个视频、图片、截图、路线视频片段、素材片段按顺序合成一个 MP4，或需要图片转视频片段后与视频拼接、统一尺寸/帧率/像素格式、生成竖屏/横屏成片、concat videos/images、compose media with ffmpeg 时使用。该 skill 自包含 Python 脚本和 FFmpeg 命令构造逻辑，不依赖 skill 文件夹之外的项目代码；只要求系统安装 ffmpeg/ffprobe。
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
    os:
      - darwin
      - linux
---

# ffmpeg-media-compose

## Environment

At the start of every skill run, load environment variables from `$OPENCLAW_HOME/.env` (defaults to `~/.openclaw/.env`) if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill to concatenate videos and images into a single MP4 with FFmpeg.

## What It Does

- Accepts videos and images in order.
- Converts images into fixed-duration video segments.
- Normalizes every segment to the same width, height, fps, SAR, and `yuv420p` pixel format.
- Concatenates normalized segments into one MP4.
- Returns structured JSON with output path, URI, duration, dimensions, and per-segment metadata.

## Boundary

This skill is standalone. Do not import or read project code outside this skill folder. The implementation lives in `scripts/compose_media.py` and only depends on:

- Python standard library.
- `ffmpeg`.
- `ffprobe`.
- User-provided media file paths.

Generated work files and outputs should stay under the chosen `--out-dir`, unless the user explicitly provides an absolute output path.

## Quick Start

```bash
cd .openclaw_skill/ffmpeg-media-compose
python3 scripts/compose_media.py \
  --inputs /path/a.mp4 /path/b.jpg /path/c.mov \
  --output composed.mp4 \
  --out-dir out \
  --image-duration 3 \
  --width 1080 \
  --height 1920 \
  --fps 30
```

The script prints JSON like:

```json
{
  "uri": "file:///.../out/composed.mp4",
  "path": "/.../out/composed.mp4",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "duration_sec": 12.0,
  "segments": []
}
```

## Manifest Input

Use a manifest when items need different image durations, trim starts, or trim lengths.

```json
{
  "output": "travel_mix.mp4",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "image_duration": 3,
  "items": [
    {"path": "/path/intro.png", "type": "image", "duration": 2.5},
    {"path": "/path/route.mp4", "type": "video", "start": 1.0, "duration": 8.0},
    {"path": "/path/photo.jpg", "type": "image", "duration": 3.0}
  ]
}
```

Run:

```bash
python3 scripts/compose_media.py --manifest manifest.json --out-dir out
```

## Defaults

- Default output: `composed.mp4`.
- Default output directory: `out`.
- Default image duration: `3s`.
- Default canvas: `1080x1920`.
- Default fps: `30`.
- Audio is stripped to keep mixed image/video concatenation reliable.

## When To Use Which Shape

- Use `1080x1920` for mobile/short-video style output.
- Use `1920x1080` for route videos, desktop previews, or landscape material.
- Use manifest input for precise trimming and mixed durations.
- Use direct `--inputs` for simple ordered concatenation.

## Error Handling

If FFmpeg is missing, input files are missing, or a segment cannot be rendered, the script exits non-zero and prints a JSON error object with `degraded: true`.

When reporting back to the user, include:

- Output path or URI if successful.
- Segment count and total duration.
- Any failed file path and FFmpeg error summary if failed.
