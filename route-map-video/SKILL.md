---
name: route-map-video
description: Generate reusable map route videos as MP4 files with a map tile background, animated route line, and vehicle marker. Use this whenever the user asks for route video, map animation, dynamic path on a map, train/high-speed rail route video, flight/airplane route animation, or wants a route such as Shanghai to Beijing rendered as a video. This skill is especially appropriate for intercity train and flight routes where the full route must fit in frame.
---

# Route Map Video

Use this skill to generate a 16:9 MP4 route animation from configurable parameters. It renders an AMap/Autonavi tile background, draws the route progressively, and moves a vehicle marker along the path.

Supported vehicle modes:

- `train`: high-speed rail style marker and green route.
- `flight`: airplane marker and blue route.

The renderer automatically chooses a map zoom level from the route bounds so long intercity routes, such as Shanghai to Beijing or Beijing to Guangzhou, fit inside the frame.

## Environment

The skill is self-contained in this folder. Do not import or depend on project repository files when using it.

Requirements:

- Node.js 18+.
- npm dependencies installed in this skill folder.
- Network access to public AMap/Autonavi map tiles.
- Chrome or Chromium. The script uses `REMOTION_BROWSER_EXECUTABLE` or `CHROME_PATH` when set, otherwise it tries common macOS Chrome locations before letting Remotion download Chrome Headless Shell.

If `node_modules` is missing, install once from the skill directory:

```bash
npm install
```

## Command

Run from this skill directory:

```bash
node scripts/generate-route-map-video.mjs --from 上海 --to 北京 --mode train --out-dir out/shanghai-beijing-train
```

Outputs:

- `route-spec.json`: exact rendered route spec.
- `route-map-video.mp4`: generated MP4.

## Parameters

Required:

- `--from <place>`: start city/place. Known city names are supported, or use `Name:lng,lat`.
- `--to <place>`: end city/place. Known city names are supported, or use `Name:lng,lat`.
- `--mode train|flight`: vehicle and route style.

Optional:

- `--via <place;place;...>`: intermediate points. Use this to shape a high-speed rail line through known cities, for example `--via "苏州;南京;徐州;济南;天津"`.
- `--title <text>`: title shown in the lower-right corner and metadata.
- `--out-dir <path>`: output directory. Defaults to `out/<timestamp>-<mode>`.
- `--duration <seconds>`: video length, default `10`.
- `--width <px>` and `--height <px>`: output size, default `1920x1080`.
- `--distance-meters <n>`: displayed route distance. If absent, calculated from path geometry.
- `--travel-seconds <n>`: displayed route travel time. If absent, estimated from mode.
- `--cost <n>`: displayed cost in RMB.
- `--input-file <json>`: render a prebuilt route spec instead of deriving one from parameters.
- `--spec-only`: write `route-spec.json` without rendering MP4.

## Place Format

Use a known city name when possible:

```bash
--from 上海 --to 北京
```

For unknown places, pass explicit coordinates:

```bash
--from "上海虹桥:121.327,31.200" --to "北京南站:116.379,39.865"
```

Coordinates are `[lng, lat]`.

## Recommended Patterns

For high-speed rail, pass `--via` to make the route look like a plausible rail corridor rather than a simple curved line:

```bash
node scripts/generate-route-map-video.mjs \
  --from 上海 \
  --to 北京 \
  --mode train \
  --via "苏州;南京;徐州;济南;天津" \
  --title "上海 → 北京 高铁路线" \
  --duration 10 \
  --cost 553 \
  --out-dir out/shanghai-beijing-train
```

For flights, omit `--via` unless the user explicitly wants a transfer or shaped path. The script will use a smooth arc:

```bash
node scripts/generate-route-map-video.mjs \
  --from 北京 \
  --to 广州 \
  --mode flight \
  --title "北京 → 广州 航线动画" \
  --duration 10 \
  --out-dir out/beijing-guangzhou-flight
```

## Output Report

After generation, report:

- MP4 path.
- Route spec path.
- Mode and route assumptions, especially via points.
- Width, height, duration.
- Any failure details from Remotion or missing dependencies.

Never claim success until `route-map-video.mp4` exists and is a real MP4 file. Prefer verifying with `ffprobe` or `file` when available.

## Troubleshooting

If rendering fails because dependencies are missing, run:

```bash
npm install
```

If the map appears too zoomed in or cropped, use `--via` to add meaningful route points. The camera still auto-fits the current segment bounds, but richer route points make the animation more legible.

If a place name is unknown, use explicit `Name:lng,lat` coordinates.
