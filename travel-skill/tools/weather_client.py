from __future__ import annotations

import json
import urllib.parse
import urllib.request

from config import REQUEST_TIMEOUT, WEATHER_BASE_URL, WEATHER_KEY
from tool_types import ApiResult, WeatherCurrent, WeatherForecastItem, WeatherResult

CITY_CODE_MAP = {"郴州": "101250201", "清远": "101280901", "衡阳": "101250401", "长沙": "101250101", "深圳": "101280601", "上海": "101020100", "杭州": "101210101", "成都": "101270101", "重庆": "101040100", "广州": "101280101", "北京": "101010100"}


def _http_get(url: str) -> dict:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_advice(current: WeatherCurrent, forecast: list[WeatherForecastItem]) -> list[str]:
    advice: list[str] = []
    if current.weather in {"雨", "小雨", "中雨", "大雨", "雷阵雨"}:
        advice.append("今天更适合安排室内景点或商圈，记得带雨具。")
    else:
        advice.append("当前天气整体适合常规出游，可优先安排户外景点。")
    if current.temperature.isdigit() and int(current.temperature) >= 30:
        advice.append("气温偏高，建议避开正午长时间暴晒。")
    if any(item.day_weather in {"大雨", "暴雨", "雷阵雨"} for item in forecast):
        advice.append("未来几天有明显降雨，路线里最好准备室内备选点。")
    return advice


def resolve_city_code(city: str) -> str:
    return CITY_CODE_MAP.get(city, city)


def get_current_weather(city: str) -> ApiResult:
    if not WEATHER_KEY:
        return ApiResult(ok=False, source="qweather", error="缺少 WEATHER_KEY 环境变量")
    query = urllib.parse.urlencode({"location": resolve_city_code(city), "key": WEATHER_KEY})
    try:
        payload = _http_get(f"{WEATHER_BASE_URL}/weather/now?{query}")
        now = payload.get("now", {})
        current = WeatherCurrent(weather=now.get("text", ""), temperature=now.get("temp", ""), humidity=now.get("humidity", ""), wind_direction=now.get("windDir", ""), wind_power=now.get("windScale", ""), report_time=payload.get("updateTime", ""))
        return ApiResult(ok=True, source="qweather", data=current)
    except Exception as exc:
        return ApiResult(ok=False, source="qweather", error=str(exc))


def get_forecast(city: str, days: int = 3) -> ApiResult:
    if not WEATHER_KEY:
        return ApiResult(ok=False, source="qweather", error="缺少 WEATHER_KEY 环境变量")
    query = urllib.parse.urlencode({"location": resolve_city_code(city), "key": WEATHER_KEY})
    try:
        payload = _http_get(f"{WEATHER_BASE_URL}/weather/3d?{query}")
        forecast = [WeatherForecastItem(date=item.get("fxDate", ""), day_weather=item.get("textDay", ""), night_weather=item.get("textNight", ""), day_temp=item.get("tempMax", ""), night_temp=item.get("tempMin", ""), day_wind=item.get("windDirDay", ""), day_power=item.get("windScaleDay", "")) for item in payload.get("daily", [])[:days]]
        return ApiResult(ok=True, source="qweather", data=forecast)
    except Exception as exc:
        return ApiResult(ok=False, source="qweather", error=str(exc))


def build_weather_summary(city: str) -> ApiResult:
    current_result = get_current_weather(city)
    if not current_result.ok:
        return current_result
    forecast_result = get_forecast(city)
    if not forecast_result.ok:
        return forecast_result
    summary = WeatherResult(city=city, current=current_result.data, forecast=forecast_result.data, travel_advice=_build_advice(current_result.data, forecast_result.data))
    return ApiResult(ok=True, source="qweather", data=summary)
