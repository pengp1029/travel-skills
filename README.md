# OpenClaw Travel Agent Skills

This folder contains a travel vertical agent skill bundle for OpenClaw. Use `travel-agent-orchestrator` as the entry skill; it routes to sub-skills for base travel planning, per-user travel memory and plan management, multi-user travel planning, Dianping research, trip map generation, and 12306 train queries.

## Structure

```text
.openclaw_skill/
├── travel-agent-orchestrator/          # Main router and travel-agent experience
├── itinerary-methodology/              # Itinerary planning methodology and schema scaffolds
├── itinerary-evidence-router/          # Evidence routing matrix for existing travel skills
├── itinerary-refine-memory/            # Plan recall, patch, diff, and versioning methodology
├── itinerary-deliverable-orchestrator/ # Map/video/card handoff methodology
├── travel-skill/                       # Base travel planning, per-user memory, weather, AMap route, web search
├── multi-user-travel-planner/          # Group-chat-only preference recall, same-city compromise points, shared city ranking
├── dianping-info-query/                # Dianping shop, rating, comment tag, and district research
├── trip-map-builder/                   # Plan/research/build workflow and Leaflet HTML template
└── train-query/                        # Read-only 12306 train ticket, station, and route queries
```

## Environment

Required for the full bundle:

```bash
python3 --version
node --version
npm --version
npm install -g @jackwener/opencli
opencli doctor
```

Environment variables used by the travel tools:

```bash
AMAP_KEY=
WEATHER_KEY=
TRAVEL_SKILL_REQUEST_TIMEOUT=10
WEB_SEARCH_BASE_URL=https://api.duckduckgo.com/
```

> ⚠️ **密钥需自行准备（Bring Your Own Keys）**
>
> 本仓库**不包含任何真实的 API Key、AK/SK、Token 或账号凭证**，上面的变量均为空占位符，需你自行申请并填入。
>
> - `AMAP_KEY`：高德开放平台 Web 服务 Key，用于地理编码、POI 搜索和路线规划（<https://lbs.amap.com/>）。部分 skill 也支持 `AMAP_WEB_SERVICE_KEY`。
> - `WEATHER_KEY`：和风天气 API Key，用于天气摘要（<https://dev.qweather.com/>）。
>
> **请勿将密钥硬编码进代码或提交到仓库。** 推荐将上述变量写入本地 `.env` 文件（例如 `~/.openclaw/.env`），各 skill 会在运行时自动加载；`.env` 文件应通过 `.gitignore` 排除，切勿提交。运行时工具只会读取环境变量，绝不会打印密钥值。

### Skill 安装路径（OPENCLAW_HOME）

各 skill 及其脚本默认安装在 `~/.openclaw/skills/` 下（例如 `~/.openclaw/skills/travel-skill/`、`~/.openclaw/skills/xiaohongshu-skills/`）。仓库内的脚本与文档不再硬编码任何绝对路径，而是按如下顺序解析根目录：

1. 环境变量 `OPENCLAW_HOME`（若已设置）；
2. 否则回退到当前用户主目录下的 `~/.openclaw`。

如果你把 skill 安装到了非默认位置，只需设置 `OPENCLAW_HOME` 即可，无需改动任何脚本：

```bash
export OPENCLAW_HOME="/your/custom/openclaw"
```

文档示例命令中出现的 `$HOME/.openclaw/...` 或 `$HOME/.comate/...` 均为占位路径，请按你的实际安装位置替换。脚本命令行参数（如 `--xhs-skill-dir`、`--collector-script`）的默认值也会据此自动推导。

For `train-query`, install Python dependencies:

```bash
pip install requests
```

For Dianping and Xiaohongshu research, sign in with Chrome where needed and keep the OpenCLI Browser Bridge extension available. Xiaohongshu CDP research uses a debuggable Chrome session on port `9223`.

## Recommended OpenClaw Usage

Install or expose this directory as an OpenClaw skill workspace, then start with `travel-agent-orchestrator` for user-facing travel requests. Use the `itinerary-*` skills as methodology layers: they define planning schemas, evidence routing, refinement/version contracts, and deliverable handoff patterns, while existing travel skills perform concrete lookup or generation work. The sub-skills can also be invoked directly when the user asks for a narrow task such as `查高铁余票` or `查大众点评评分`.

For ongoing itinerary work, use `travel-skill/scripts/memory.py` with a stable `--user-id` to keep each user's plans and preferences isolated. It supports `save-plan`, `recall`, `modify-plan`, `extract-preferences`, and `show-preferences`. Only in explicit group-chat travel planning, `multi-user-travel-planner` treats group member Feishu ids as stable user ids, recalls each participant separately, and combines coarse origins and preferences without merging private memory stores. In one-on-one chats or personal planning, use the general travel planning flow instead. Set `TRAVEL_MEMORY_DIR` when testing or when memory should live outside the default `.travel_memory/` directory.

## Capability Boundaries

This bundle can provide planning recommendations, per-user plan recall and modification, travel preference memory, group-chat-only multi-user preference fusion, same-city compromise point planning, afternoon/evening group activity planning, shared destination city ranking, route checks, weather summaries, restaurant research, map-page generation, and read-only train ticket queries. It does not provide real-time crowd counts, real-time queue minutes, ticket locking, hotel price locking, payment, train booking, train waitlist, ticket changes, automatic refunds, or automatic access to private Feishu profile data beyond user-provided stable ids. Travel memory should store only travel-related preferences, coarse origin areas, and plans, not phone numbers, government IDs, precise home addresses, payment data, login state, or ticket credentials.
