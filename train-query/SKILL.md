---
name: train-query
description: >
  12306 高铁/火车只读查询 skill。用于查询中国铁路车站编码、城市下车站、直达余票、中转余票、车次经停站、出发到达时间、席别余票和价格。用户问高铁余票、火车票还有没有、某天从 A 到 B 怎么坐、车站 code、车次停靠站时使用。只做查询和行程决策辅助，不提供订票、候补、改签、退票、支付或登录态操作，也可由 travel-agent-orchestrator 调用补充城际交通事实。
metadata:
  openclaw:
    requires:
      bins:
        - python3
      python:
        - requests
    os:
      - darwin
      - linux
---

# train-query

## Environment

At the start of every skill run, load environment variables from `$OPENCLAW_HOME/.env` (defaults to `~/.openclaw/.env`) if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill for read-only 12306 railway facts inside travel planning.

## Capabilities

- Get the current date in `Asia/Shanghai` for relative-date parsing.
- Query all train stations in a city.
- Query representative city station codes.
- Query station code by station name.
- Query station detail by telecode.
- Query direct ticket availability with filters, sorting, time windows, and output format.
- Query interline/transfer options when direct trains are unavailable or undesirable.
- Query train route stations by train code and date.

## Boundaries

This skill is strictly read-only. Do not claim it can book, lock, pay, waitlist, change, refund, choose seats, log into an account, or guarantee inventory. 12306 availability changes quickly; present results as a snapshot and include query time/date when useful.

## Quick Start

Run commands from this skill directory:

```bash
python scripts/12306_apis.py list-tools
python scripts/12306_apis.py get-current-date
python scripts/12306_apis.py get-stations-code-in-city --city "北京"
python scripts/12306_apis.py get-station-code-by-names --station_names "北京南|上海虹桥"
python scripts/12306_apis.py get-tickets --date "2026-07-01" --from_station "北京南" --to_station "上海虹桥" --train_filter_flags "G" --sort_flag duration --limited_num 5 --format text
python scripts/12306_apis.py get-interline-tickets --date "2026-07-01" --from_station "成都" --to_station "广州" --limited_num 5 --format text
python scripts/12306_apis.py get-train-route-stations --train_code "G1033" --depart_date "2026-07-01"
```

## Tool Commands

- `list-tools`: list available commands.
- `refresh-cache`: refresh local station and query-path cache; avoid unless cache looks stale.
- `get-current-date`: current date in `Asia/Shanghai`, format `YYYY-MM-DD`.
- `get-stations-code-in-city`: city -> all stations.
- `get-station-code-of-citys`: one or more city names separated by `|` -> representative station code.
- `get-station-code-by-names`: one or more station names separated by `|` -> telecodes.
- `get-station-by-telecode`: telecode -> station detail.
- `get-tickets`: direct ticket availability.
- `get-interline-tickets`: transfer ticket availability.
- `get-train-route-stations`: route stops for a train code and date.

## Decision Use

When orchestrating travel plans:

1. Resolve station names first if the user gave city names or ambiguous station names.
2. Prefer direct `G/D/C` trains for short-trip planning unless the user asks for cheap/slow options.
3. Use `limited_num` and time filters to keep output small.
4. Summarize the best 3-5 options by departure time, arrival time, duration, seats, and price.
5. State that ticket availability is a snapshot and requires final confirmation on official 12306 or booking app.
