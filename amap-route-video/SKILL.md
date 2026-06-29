---
name: amap-route-video
description: >
  高德 API 行程路径视频生成 skill。用户想把一段旅行路线、城市动线、景点之间的步行/骑行/驾车/公交地铁路径生成路线视频、路径动画、行程视频、Remotion MP4、AMap route video 时使用。这个 skill 自包含高德路线查询、路线 spec 生成、Remotion 渲染组件和脚本；执行时不要引用 skill 文件夹之外的项目代码或资源，只允许使用本 skill 目录内文件、npm 依赖和外部高德/地图瓦片 API。
metadata:
  openclaw:
    requires:
      bins:
        - node
        - npm
        - npx
      env:
        - AMAP_KEY
        - AMAP_WEB_SERVICE_KEY
    os:
      - darwin
      - linux
---

# amap-route-video

## Environment

At the start of every skill run, load environment variables from `/Users/user/.openclaw/.env` if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill to generate a 16:9 MP4 route video from a travel route using AMap Web Service APIs and Remotion.

## Self-Contained Boundary

This skill is intentionally standalone. Do not import or read files from outside this skill folder. All runtime code is bundled here:

- `scripts/plan-to-route-spec.mjs`: parses natural language route text.
- `scripts/amap-route-client.mjs`: calls AMap geocoding and route APIs.
- `scripts/generate-route-video.mjs`: writes route spec and renders MP4.
- `src/`: Remotion entry, component, route defaults, and geo helpers.
- `package.json` and `remotion.config.mjs`: local render environment.

Allowed external dependencies are npm packages installed from this folder and network calls to AMap APIs / AMap map tiles.

## Requirements

- Node.js 18+.
- npm.
- AMap Web Service key in `AMAP_KEY` or `AMAP_WEB_SERVICE_KEY`.
- Remotion dependencies installed inside this skill folder.

```bash
cd .openclaw_skill/amap-route-video
npm install
export AMAP_KEY="..."
```

## Generate A Route Video

```bash
node scripts/generate-route-video.mjs --plan "雍和宫->什刹海步行一段，什刹海->王府井地铁一段"
```

Outputs stay inside this skill folder:

- `out/route-spec.json`
- `src/route/generatedRouteSpec.js`
- `out/amap-segmented-route.mp4`

## Input Formats

### Natural Language Route

Use `--plan` for route text. Segment separators can be commas or Chinese punctuation. Segment arrows can be `->`, `到`, `至`, or `→`.

Examples:

```bash
node scripts/generate-route-video.mjs --plan "从西湖到河坊街步行，河坊街到杭州东站地铁"
node scripts/generate-route-video.mjs --plan "天安门->故宫步行，故宫->三里屯驾车"
```

Supported modes:

- `walking`: 步行 / walk.
- `bicycling`: 骑行 / bike.
- `driving`: 驾车 / drive.
- `transit`: 地铁 / 公交 / subway / bus.

### JSON Route Spec Or Plan

Use `--input-file <path>` for JSON. If the JSON already contains `segments[].path`, it is treated as a ready route spec and rendered directly. Otherwise it is treated as a plan and expanded through AMap APIs.

Plan shape:

```json
{
  "title": "西湖到杭州东站",
  "city": "杭州",
  "segments": [
    {"from": "西湖", "to": "河坊街", "mode": "walking"},
    {"from": "河坊街", "to": "杭州东站", "mode": "transit", "preferredVehicle": "subway"}
  ]
}
```

Route spec shape:

```json
{
  "title": "西湖到杭州东站",
  "city": "杭州",
  "segments": [
    {
      "mode": "walking",
      "label": "步行",
      "color": "#1d6fea",
      "from": {"name": "西湖", "coordinates": [120.143, 30.25]},
      "to": {"name": "河坊街", "coordinates": [120.17, 30.24]},
      "path": [[120.143, 30.25], [120.17, 30.24]],
      "distanceMeters": 2000,
      "durationSeconds": 1600,
      "steps": [{"mode": "步行", "text": "沿高德规划路线步行"}]
    }
  ]
}
```

## Validate Without Rendering

Use `--spec-only` to call AMap and write the route spec without rendering MP4:

```bash
node scripts/generate-route-video.mjs --plan "雍和宫->什刹海步行" --spec-only
```

This is useful for checking API keys, city ambiguity, and route parsing before running Remotion.

## Output Rules

When using this skill for a user request, report:

- The generated video path.
- The route spec path.
- Any route mode assumptions.
- Any AMap errors or ambiguity that need user correction.

Never claim the output is generated until `out/amap-segmented-route.mp4` exists.
