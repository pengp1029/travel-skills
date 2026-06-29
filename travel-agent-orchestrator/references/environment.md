# Environment

## Required Runtime

- Python 3.10+
- Node.js and npm
- Chrome when browser-based research is needed
- OpenCLI for Dianping/Xiaohongshu research and browser bridge workflows

## Install

```bash
python3 --version
node --version
npm --version
npm install -g @jackwener/opencli
opencli doctor
pip install requests
```

## Environment Variables

```bash
export AMAP_KEY="..."
export WEATHER_KEY="..."
export WEB_SEARCH_BASE_URL="https://api.duckduckgo.com/"
export TRAVEL_SKILL_REQUEST_TIMEOUT=10
```

## Browser Login

For Dianping or Xiaohongshu research, the browser may need to be logged into the target site. If login blocks research, ask the user to complete login in Chrome and retry. Do not ask for passwords or cookies.

## Installation Layout

Install/copy the whole `.openclaw_skill` directory as a bundle so the orchestrator can reference sibling sub-skills:

```text
.openclaw_skill/
├── travel-agent-orchestrator/
├── travel-skill/
├── dianping-info-query/
├── trip-map-builder/
└── train-query/
```
