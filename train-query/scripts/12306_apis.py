#!/usr/bin/env python3
"""Read-only 12306 query CLI for OpenClaw travel skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from functools import cmp_to_key
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.dirname(SCRIPT_DIR)
API_BASE = "https://kyfw.12306.cn"
SEARCH_API_BASE = "https://search.12306.cn"
WEB_URL = "https://www.12306.cn/index/"
LCQUERY_INIT_URL = "https://kyfw.12306.cn/otn/lcQuery/init"
VERSION = "0.1.0-openclaw"

STATION_KEYS = ["station_id", "station_name", "station_code", "station_pinyin", "station_short", "station_index", "code", "city", "r1", "r2"]
TICKET_KEYS = ["secret_Sstr", "button_text_info", "train_no", "station_train_code", "start_station_telecode", "end_station_telecode", "from_station_telecode", "to_station_telecode", "start_time", "arrive_time", "lishi", "canWebBuy", "yp_info", "start_train_date", "train_seat_feature", "location_code", "from_station_no", "to_station_no", "is_support_card", "controlled_train_flag", "gg_num", "gr_num", "qt_num", "rw_num", "rz_num", "tz_num", "wz_num", "yb_num", "yw_num", "yz_num", "ze_num", "zy_num", "swz_num", "srrb_num", "yp_ex", "seat_types", "exchange_train_flag", "houbu_train_flag", "houbu_seat_limit", "yp_info_new", "40", "41", "42", "43", "44", "45", "dw_flag", "47", "stopcheckTime", "country_flag", "local_arrive_time", "local_start_time", "52", "bed_level_info", "seat_discount_info", "sale_time", "56"]
SEATS = {"9": ("商务座", "swz"), "P": ("特等座", "tz"), "M": ("一等座", "zy"), "D": ("优选一等座", "zy"), "O": ("二等座", "ze"), "S": ("二等包座", "ze"), "6": ("高级软卧", "gr"), "A": ("高级动卧", "gr"), "4": ("软卧", "rw"), "I": ("一等卧", "rw"), "F": ("动卧", "rw"), "3": ("硬卧", "yw"), "J": ("二等卧", "yw"), "2": ("软座", "rz"), "1": ("硬座", "yz"), "W": ("无座", "wz"), "WZ": ("无座", "wz"), "H": ("其他", "qt")}
DW_FLAGS = ["智能动车组", "复兴号", "静音车厢", "温馨动卧", "动感号", "支持选铺", "老年优惠"]
MISSING_STATIONS = [{"station_id": "@cdd", "station_name": "成  都东", "station_code": "WEI", "station_pinyin": "chengdudong", "station_short": "cdd", "station_index": "", "code": "1707", "city": "成都", "r1": "", "r2": ""}]

STATIONS: dict[str, dict[str, str]] = {}
CITY_STATIONS: dict[str, list[dict[str, str]]] = {}
CITY_CODES: dict[str, dict[str, str]] = {}
NAME_STATIONS: dict[str, dict[str, str]] = {}
LCQUERY_PATH = ""
COOKIES: dict[str, str] | None = None


def request_get(url: str, params: dict[str, str] | None = None, cookies: dict[str, str] | None = None, return_text: bool = False) -> Any:
    try:
        full_url = f"{url}?{urlencode(params)}" if params else url
        response = requests.get(full_url, cookies=cookies, timeout=12)
        response.raise_for_status()
        return response.text if return_text else response.json()
    except Exception as error:
        print(f"Error requesting 12306: {error}", file=sys.stderr)
        return None


def get_cookie() -> dict[str, str] | None:
    global COOKIES
    if COOKIES:
        return COOKIES
    try:
        COOKIES = requests.get(f"{API_BASE}/otn/leftTicket/init", timeout=12).cookies.get_dict()
        return COOKIES
    except Exception as error:
        print(f"Error getting cookie: {error}", file=sys.stderr)
        return None


def parse_stations(raw: str) -> dict[str, dict[str, str]]:
    parts = raw.split("|")
    result: dict[str, dict[str, str]] = {}
    for i in range(0, len(parts) // 10 * 10, 10):
        station = {k: parts[i + n] for n, k in enumerate(STATION_KEYS)}
        if station.get("station_code"):
            result[station["station_code"]] = station
    for station in MISSING_STATIONS:
        result.setdefault(station["station_code"], station)
    return result


def fetch_stations() -> dict[str, dict[str, str]]:
    html = request_get(WEB_URL, return_text=True)
    if not isinstance(html, str):
        raise RuntimeError("failed to fetch 12306 homepage")
    match = re.search(r"\./script/core/common/station_name.+?\.js", html)
    if not match:
        raise RuntimeError("failed to locate station script")
    js = request_get(WEB_URL + match.group(0)[1:], return_text=True)
    raw = re.search(r"station_names\s*=\s*'([^']+)'", js or "")
    if not raw:
        raise RuntimeError("failed to parse station script")
    return parse_stations(raw.group(1))


def fetch_lcquery_path() -> str:
    html = request_get(LCQUERY_INIT_URL, return_text=True)
    match = re.search(r" var lc_search_url = '(.+?)'", html or "")
    if not match:
        raise RuntimeError("failed to parse lcquery path")
    return match.group(1)


def cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, name)


def init(force: bool = False) -> None:
    global STATIONS, CITY_STATIONS, CITY_CODES, NAME_STATIONS, LCQUERY_PATH
    stations_file = cache_path("stations.json")
    lc_file = cache_path("lcquery_path")
    fresh = lambda p: os.path.exists(p) and os.path.getmtime(p) > time.time() - 86400

    if not force and fresh(lc_file):
        with open(lc_file, "r", encoding="utf-8") as f:
            LCQUERY_PATH = f.read().strip()
    else:
        LCQUERY_PATH = fetch_lcquery_path()
        with open(lc_file, "w", encoding="utf-8") as f:
            f.write(LCQUERY_PATH)

    if not force and fresh(stations_file):
        with open(stations_file, "r", encoding="utf-8") as f:
            STATIONS = json.load(f)
    else:
        STATIONS = fetch_stations()
        with open(stations_file, "w", encoding="utf-8") as f:
            json.dump(STATIONS, f, ensure_ascii=False)

    CITY_STATIONS = {}
    CITY_CODES = {}
    NAME_STATIONS = {}
    for station in STATIONS.values():
        city = station.get("city", "")
        item = {"station_code": station["station_code"], "station_name": station["station_name"]}
        CITY_STATIONS.setdefault(city, []).append(item)
        NAME_STATIONS[station["station_name"]] = item
    for city, stations in CITY_STATIONS.items():
        CITY_CODES[city] = next((s for s in stations if s["station_name"] == city), stations[0])


def station_code(station: str) -> str | None:
    if re.fullmatch(r"[A-Z]+", station or "") and station in STATIONS:
        return station
    name = station[:-1] if station.endswith("站") else station
    return NAME_STATIONS.get(name, {}).get("station_code")


def check_date(date: str) -> bool:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    return datetime.fromisoformat(date).date() >= today


def parse_ticket_rows(rows: list[str]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        values = row.split("|")
        out.append({key: values[i] if i < len(values) else "" for i, key in enumerate(TICKET_KEYS)})
    return out


def status(value: str) -> str:
    if value.isdigit():
        return "无票" if int(value) == 0 else f"剩余{value}张票"
    if value in {"有", "充足"}:
        return "有票"
    if value in {"无", "--", ""}:
        return "无票"
    if value == "候补":
        return "无票需候补"
    return value


def prices(yp_info: str, discount_info: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for i in range(len(yp_info) // 10):
        block = yp_info[i * 10 : (i + 1) * 10]
        code = "W" if int(block[6:10] or 0) >= 3000 else (block[0] if block[0] in SEATS else "H")
        seat_name, short = SEATS[code]
        items.append({"seat_name": seat_name, "short": short, "num": row.get(f"{short}_num", ""), "price": int(block[1:6] or 0) / 10})
    return items


def dw_flags(raw: str) -> list[str]:
    parts = (raw or "").split("#")
    result = []
    checks = [(0, "5", 0), (1, "1", 1), (5, "D", 4)]
    for index, expected, flag_index in checks:
        if len(parts) > index and parts[index] == expected:
            result.append(DW_FLAGS[flag_index])
    if len(parts) > 2 and parts[2].startswith("Q"):
        result.append("静音车厢")
    if len(parts) > 2 and parts[2].startswith("R"):
        result.append("温馨动卧")
    return result


def ticket_info(rows: list[dict[str, Any]], code_map: dict[str, str]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({
            "train_no": row.get("train_no"),
            "start_train_code": row.get("station_train_code"),
            "start_date": datetime.strptime(row.get("start_train_date", "19700101"), "%Y%m%d").strftime("%Y-%m-%d"),
            "start_time": row.get("start_time"),
            "arrive_time": row.get("arrive_time"),
            "lishi": row.get("lishi"),
            "from_station": code_map.get(row.get("from_station_telecode", ""), ""),
            "to_station": code_map.get(row.get("to_station_telecode", ""), ""),
            "from_station_telecode": row.get("from_station_telecode"),
            "to_station_telecode": row.get("to_station_telecode"),
            "prices": prices(row.get("yp_info_new", ""), row.get("seat_discount_info", ""), row),
            "dw_flag": dw_flags(row.get("dw_flag", "")),
        })
    return result


def train_match(item: dict[str, Any], flags: str) -> bool:
    code = item.get("start_train_code", "")
    if not flags:
        return True
    for flag in flags:
        if flag == "G" and (code.startswith("G") or code.startswith("C")):
            return True
        if flag in "DZTK" and code.startswith(flag):
            return True
        if flag == "O" and not code[:1] in "GCDZTK":
            return True
        if flag == "F" and "复兴号" in item.get("dw_flag", []):
            return True
        if flag == "S" and "智能动车组" in item.get("dw_flag", []):
            return True
    return False


def filter_items(items: list[dict[str, Any]], flags: str, earliest: int, latest: int, sort_flag: str, reverse: bool, limit: int) -> list[dict[str, Any]]:
    result = [x for x in items if train_match(x, flags) and earliest <= int((x.get("start_time") or "00:00").split(":")[0]) < latest]
    def cmp(a: dict[str, Any], b: dict[str, Any]) -> int:
        if sort_flag == "duration":
            ah, am = map(int, a["lishi"].split(":")); bh, bm = map(int, b["lishi"].split(":")); return (ah * 60 + am) - (bh * 60 + bm)
        key = "arrive_time" if sort_flag == "arriveTime" else "start_time"
        return (a.get(key, "") > b.get(key, "")) - (a.get(key, "") < b.get(key, ""))
    if sort_flag in {"startTime", "arriveTime", "duration"}:
        result.sort(key=cmp_to_key(cmp), reverse=reverse)
    return result if limit == 0 else result[:limit]


def format_tickets(items: list[dict[str, Any]]) -> str:
    if not items:
        return "没有查询到相关车次信息"
    lines = ["车次|出发站 -> 到达站|出发时间 -> 到达时间|历时"]
    for item in items:
        line = f"{item['start_train_code']} {item['from_station']}(telecode:{item['from_station_telecode']}) -> {item['to_station']}(telecode:{item['to_station_telecode']}) {item['start_time']} -> {item['arrive_time']} 历时：{item['lishi']}"
        for price in item["prices"]:
            line += f"\n- {price['seat_name']}: {status(str(price.get('num', '')))} {price['price']}元"
        lines.append(line)
    return "\n".join(lines)


def get_tickets(args: argparse.Namespace) -> str:
    if not check_date(args.date):
        return "Error: The date cannot be earlier than today."
    from_code, to_code = station_code(args.from_station), station_code(args.to_station)
    if not from_code or not to_code:
        return f"Error: Station not found. from_station_result: {from_code}, to_station_result: {to_code}."
    cookies = get_cookie()
    if not cookies:
        return "Error: Get cookie failed. Check your network."
    data = request_get(f"{API_BASE}/otn/leftTicket/query", {"leftTicketDTO.train_date": args.date, "leftTicketDTO.from_station": from_code, "leftTicketDTO.to_station": to_code, "purpose_codes": "ADULT"}, cookies=cookies)
    if not data or "data" not in data:
        return "Error: Get tickets data failed."
    items = ticket_info(parse_ticket_rows(data["data"].get("result", [])), data["data"].get("map", {}))
    items = filter_items(items, args.train_filter_flags, args.earliest_start_time, args.latest_start_time, args.sort_flag, args.sort_reverse, args.limited_num)
    return json.dumps(items, ensure_ascii=False) if args.format == "json" else format_tickets(items)


def get_interline(args: argparse.Namespace) -> str:
    return "中转查询请优先使用官方 12306 或完整 vendor 脚本；当前 OpenClaw 轻量脚本保留 read-only 边界，建议先查询直达余票后再人工确认中转方案。"


def get_route(args: argparse.Namespace) -> str:
    data = request_get(f"{SEARCH_API_BASE}/search/v1/train/search", {"keyword": args.train_code, "date": args.depart_date.replace("-", "")})
    if not data or not data.get("data"):
        return "很抱歉，未查询到对应车次。"
    cookies = get_cookie()
    if not cookies:
        return "Error: get cookie failed. Check your network."
    first = data["data"][0]
    route = request_get(f"{API_BASE}/otn/queryTrainInfo/query", {"leftTicketDTO.train_no": first["train_no"], "leftTicketDTO.train_date": args.depart_date, "rand_code": ""}, cookies=cookies)
    rows = (route or {}).get("data", {}).get("data", [])
    if args.format == "json":
        return json.dumps(rows, ensure_ascii=False)
    if not rows:
        return "未查询到相关车次信息。"
    lines = [f"{args.train_code}次列车经停站", "站序|车站|到达时间|出发时间|停留"]
    for i, row in enumerate(rows, 1):
        lines.append(f"{i}|{row.get('station_name')}|{row.get('arrive_time')}|{row.get('start_time')}|{row.get('stopover_time', '')}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="12306 read-only tool runner")
    sub = parser.add_subparsers(dest="tool", required=True)
    sub.add_parser("list-tools")
    sub.add_parser("refresh-cache")
    sub.add_parser("get-current-date")
    p = sub.add_parser("get-stations-code-in-city"); p.add_argument("--city", required=True)
    p = sub.add_parser("get-station-code-of-citys"); p.add_argument("--citys", required=True)
    p = sub.add_parser("get-station-code-by-names"); p.add_argument("--station_names", required=True)
    p = sub.add_parser("get-station-by-telecode"); p.add_argument("--station_telecode", required=True)
    p = sub.add_parser("get-tickets"); p.add_argument("--date", required=True); p.add_argument("--from_station", required=True); p.add_argument("--to_station", required=True); p.add_argument("--train_filter_flags", default=""); p.add_argument("--earliest_start_time", type=int, default=0); p.add_argument("--latest_start_time", type=int, default=24); p.add_argument("--sort_flag", default=""); p.add_argument("--sort_reverse", action="store_true"); p.add_argument("--limited_num", type=int, default=0); p.add_argument("--format", choices=["text", "json"], default="text")
    p = sub.add_parser("get-interline-tickets"); p.add_argument("--date", required=True); p.add_argument("--from_station", required=True); p.add_argument("--to_station", required=True); p.add_argument("--middle_station", default=""); p.add_argument("--limited_num", type=int, default=10); p.add_argument("--format", choices=["text", "json"], default="text")
    p = sub.add_parser("get-train-route-stations"); p.add_argument("--train_code", required=True); p.add_argument("--depart_date", required=True); p.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.tool == "list-tools":
        print(json.dumps({"tools": ["refresh-cache", "get-current-date", "get-stations-code-in-city", "get-station-code-of-citys", "get-station-code-by-names", "get-station-by-telecode", "get-tickets", "get-interline-tickets", "get-train-route-stations"], "version": VERSION}, ensure_ascii=False)); return 0
    if args.tool == "get-current-date":
        print(datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")); return 0
    try:
        init(force=args.tool == "refresh-cache")
        if args.tool == "refresh-cache": print("缓存刷新完成"); return 0
        if args.tool == "get-stations-code-in-city": print(json.dumps(CITY_STATIONS.get(args.city, []), ensure_ascii=False)); return 0
        if args.tool == "get-station-code-of-citys": print(json.dumps({c: CITY_CODES.get(c, {"error": "未检索到城市。"}) for c in args.citys.split("|")}, ensure_ascii=False)); return 0
        if args.tool == "get-station-code-by-names": print(json.dumps({s.rstrip("站"): NAME_STATIONS.get(s.rstrip("站"), {"error": "未检索到车站。"}) for s in args.station_names.split("|")}, ensure_ascii=False)); return 0
        if args.tool == "get-station-by-telecode": print(json.dumps(STATIONS.get(args.station_telecode, {"error": "未检索到车站。"}), ensure_ascii=False)); return 0
        if args.tool == "get-tickets": print(get_tickets(args)); return 0
        if args.tool == "get-interline-tickets": print(get_interline(args)); return 0
        if args.tool == "get-train-route-stations": print(get_route(args)); return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
