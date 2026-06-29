# Manifest Reference

## Fields

- `output`: output file name or absolute path.
- `width`: output width, default `1080`.
- `height`: output height, default `1920`.
- `fps`: output frame rate, default `30`.
- `image_duration`: default duration for images, default `3` seconds.
- `items`: ordered media list.

## Item Fields

- `path`: required local media path.
- `type`: optional, `image` or `video`; inferred from extension when omitted.
- `duration` or `duration_sec`: optional duration override.
- `start` or `start_sec`: optional video trim start in seconds.

## Example

```json
{
  "output": "mixed.mp4",
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "items": [
    {"path": "/tmp/route_1.mp4", "type": "video"},
    {"path": "/tmp/photo.jpg", "type": "image", "duration": 4},
    {"path": "/tmp/route_2.mp4", "type": "video", "start": 2, "duration": 6}
  ]
}
```
