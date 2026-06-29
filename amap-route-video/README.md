# amap-route-video

Self-contained OpenClaw skill for generating AMap route videos.

## Quick Start

```bash
cd .openclaw_skill/amap-route-video
npm install
export AMAP_KEY="..."
node scripts/generate-route-video.mjs --plan "雍和宫->什刹海步行一段，什刹海->王府井地铁一段"
```

Output:

- `out/route-spec.json`
- `out/amap-segmented-route.mp4`

## Boundary

This skill must not import files from outside `amap-route-video/`. It carries its own route parser, AMap client, Remotion component, config, and package metadata.
