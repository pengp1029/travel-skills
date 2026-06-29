from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ApiResult:
    ok: bool
    source: str
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherCurrent:
    weather: str
    temperature: str
    humidity: str
    wind_direction: str
    wind_power: str
    report_time: str


@dataclass
class WeatherForecastItem:
    date: str
    day_weather: str
    night_weather: str
    day_temp: str
    night_temp: str
    day_wind: str
    day_power: str


@dataclass
class WeatherResult:
    city: str
    current: WeatherCurrent | None = None
    forecast: list[WeatherForecastItem] = field(default_factory=list)
    travel_advice: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "current": asdict(self.current) if self.current else None,
            "forecast": [asdict(item) for item in self.forecast],
            "travel_advice": self.travel_advice,
        }


@dataclass
class PoiItem:
    name: str
    address: str
    location: str
    district: str
    poi_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteResult:
    mode: str
    origin: str
    destination: str
    distance_m: int
    duration_s: int
    summary: str
    cost: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResultItem:
    title: str
    snippet: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResultBundle:
    query: str
    items: list[SearchResultItem] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"query": self.query, "items": [item.to_dict() for item in self.items], "summary": self.summary}


@dataclass
class SnapshotMeta:
    version: str
    created_at: str
    note: str
    files: list[str]

    @classmethod
    def create(cls, version: str, note: str, files: list[str]) -> "SnapshotMeta":
        return cls(version=version, created_at=datetime.utcnow().isoformat(), note=note, files=files)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
