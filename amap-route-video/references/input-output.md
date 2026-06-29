# Input And Output

## Natural Language

```bash
node scripts/generate-route-video.mjs --plan "从西湖到河坊街步行，河坊街到杭州东站地铁"
```

## Plan JSON

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

## Ready Route Spec JSON

If `segments[].path` exists, the script skips AMap route planning and renders the route directly.

## Outputs

All generated files stay under this skill directory:

- `out/route-spec.json`
- `src/route/generatedRouteSpec.js`
- `out/amap-segmented-route.mp4`
