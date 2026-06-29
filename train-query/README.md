# train-query

Read-only 12306 query skill for OpenClaw travel agents.

## Requirements

- Python 3.10+
- `requests`

```bash
pip install requests
```

## Commands

```bash
python scripts/12306_apis.py list-tools
python scripts/12306_apis.py get-current-date
python scripts/12306_apis.py get-stations-code-in-city --city "北京"
python scripts/12306_apis.py get-tickets --date "2026-07-01" --from_station "北京南" --to_station "上海虹桥" --train_filter_flags "G" --limited_num 5
```

## Notes

- Results are live snapshots from public 12306 endpoints.
- This skill does not book, lock inventory, pay, waitlist, change, or refund tickets.
- Use filters to reduce output size in agent responses.
