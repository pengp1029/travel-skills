"""
Capability matrix for existing travel skills.

This matrix is descriptive. It does not invoke skills or guarantee availability.
Agents should use it to choose the smallest adequate downstream capability.
"""

CAPABILITY_MATRIX: dict[str, dict[str, object]] = {
    "poi_basic": {
        "preferred_skill": "travel-skill",
        "elements": ["景点", "街区", "POI", "开放时间", "门票", "预约政策", "高德路线", "天气"],
        "evidence_level": "hard_fact",
        "required_when": "POI or route facts affect itinerary execution.",
    },
    "restaurant_local_life": {
        "preferred_skill": "dianping-info-query",
        "elements": ["餐厅", "商圈", "评分", "人均", "营业时间", "推荐菜", "评论标签", "排队", "踩雷"],
        "evidence_level": "structured_signal",
        "required_when": "Food or local-life choices affect route quality or risk.",
    },
    "railway": {
        "preferred_skill": "train-query",
        "elements": ["车站", "高铁", "火车", "余票", "中转", "车次", "经停", "席别", "价格"],
        "evidence_level": "hard_fact_snapshot",
        "required_when": "Intercity transport constrains arrival or departure timing.",
    },
    "xhs_atmosphere": {
        "preferred_skill": "xiaohongshu-skills",
        "elements": ["小红书", "氛围", "拍照", "近期体验", "避坑", "种草"],
        "evidence_level": "soft_signal",
        "required_when": "Taste, vibe, photo-friendliness, or recent subjective signals matter.",
    },
    "poi_images": {
        "preferred_skill": "poi-image-collector",
        "elements": ["图片", "素材", "封面", "预览图", "source_url", "imageUrl"],
        "evidence_level": "deliverable_asset",
        "required_when": "Map cards, Feishu cards, or videos need image/source fields.",
    },
    "map_deliverable": {
        "preferred_skill": "trip-map-builder",
        "elements": ["地图", "HTML", "Leaflet", "点位卡片", "导航链接", "可分享页面"],
        "evidence_level": "deliverable",
        "required_when": "The user asks for a map or shareable trip page.",
    },
    "video_deliverable": {
        "preferred_skill": "travel-vlog-video",
        "elements": ["vlog", "视频", "路线视频", "MP4", "时间线"],
        "evidence_level": "deliverable",
        "required_when": "The user asks to turn an itinerary into video content.",
    },
}


def get_capability_matrix() -> dict[str, dict[str, object]]:
    """Expose routing hints for agents."""
    return CAPABILITY_MATRIX
