"""
Deliverable handoff contracts for itinerary assets.

This script does not generate files. It defines required and optional fields for
agents to pass to downstream skills.
"""

DELIVERABLES: dict[str, dict[str, object]] = {
    "map": {
        "suggested_skill": "trip-map-builder",
        "required_inputs": ["city", "days.locations.name", "days.locations.lat", "days.locations.lng"],
        "optional_inputs": ["detailUrl", "imageUrl", "dianpingUrl", "xhsUrl", "sourceNote", "feishuCard"],
    },
    "vlog": {
        "suggested_skill": "travel-vlog-video",
        "required_inputs": ["city", "ordered_points", "adjacent_route_legs"],
        "optional_inputs": ["image_path", "image_url", "route_mode", "caption_style"],
    },
    "route_video": {
        "suggested_skill": "amap-route-video",
        "required_inputs": ["city", "segments.from", "segments.to", "segments.mode"],
        "optional_inputs": ["title", "style"],
    },
    "image_pack": {
        "suggested_skill": "poi-image-collector",
        "required_inputs": ["city", "pois.name", "pois.type"],
        "optional_inputs": ["preferred_sources", "max_images_per_poi", "usage"],
    },
    "media_compose": {
        "suggested_skill": "ffmpeg-media-compose",
        "required_inputs": ["media_items"],
        "optional_inputs": ["resolution", "fps", "audio", "layout"],
    },
}


def get_deliverable_contract(kind: str | None = None) -> dict[str, object]:
    """Return one deliverable contract or all contracts."""
    if kind:
        return DELIVERABLES.get(kind, {})
    return DELIVERABLES
