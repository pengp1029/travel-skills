# ffmpeg-media-compose

Self-contained OpenClaw skill for composing videos and images into one MP4 with FFmpeg.

## Requirements

```bash
ffmpeg -version
ffprobe -version
python3 --version
```

## Quick Start

```bash
cd .openclaw_skill/ffmpeg-media-compose
python3 scripts/compose_media.py \
  --inputs /path/a.mp4 /path/b.jpg /path/c.mov \
  --output composed.mp4 \
  --out-dir out
```

## Manifest

```json
{
  "output": "travel_mix.mp4",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "image_duration": 3,
  "items": [
    {"path": "/path/intro.png", "type": "image", "duration": 2.5},
    {"path": "/path/route.mp4", "type": "video", "start": 1.0, "duration": 8.0}
  ]
}
```

```bash
python3 scripts/compose_media.py --manifest manifest.json --out-dir out
```

## Boundary

The script does not import project modules outside this skill. It uses only Python standard library plus installed `ffmpeg` and `ffprobe`.
