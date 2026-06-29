# travel-skill 安装说明

## 环境要求

- Python 3.10+
- Git
- 可选：高德地图 API Key
- 可选：和风天气 API Key

## OpenClaw 安装位置

```bash
cp -R travel-skill ~/.openclaw/workspace/skills/travel-skill
```

如果从本仓库使用，直接让 OpenClaw 读取 `.openclaw_skill/travel-skill` 即可。

## 环境变量

```bash
AMAP_KEY=
WEATHER_KEY=
TRAVEL_SKILL_REQUEST_TIMEOUT=10
WEB_SEARCH_BASE_URL=https://api.duckduckgo.com/
```

说明：

- `AMAP_KEY`：地理编码、POI 搜索和路线规划。
- `WEATHER_KEY`：天气查询。
- `TRAVEL_SKILL_REQUEST_TIMEOUT`：请求超时，单位秒。
- `WEB_SEARCH_BASE_URL`：联网搜索接口地址。

## 使用建议

- 常规“去哪玩 / 去哪吃 / 怎么安排”走推荐逻辑。
- 问天气时调用天气工具。
- 问路线时调用高德工具。
- 问最新开放时间、票价、政策时调用联网搜索工具。
