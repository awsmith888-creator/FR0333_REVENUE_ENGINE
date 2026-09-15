from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from math import asin, cos, radians, sin, sqrt
from statistics import fmean
from typing import Iterable, Mapping, Sequence

ADOBE_LOGICAL_SLOT_COUNT = 64
FR0333_WEATHER_RAIL_VERSION = "1.0.5-FINAL"


class EvidenceClass(StrEnum):
    E_OBS = "E_OBS"
    E_MES = "E_MES"


class WeatherUse(StrEnum):
    TEMPORAL_BASELINE = "TEMPORAL_BASELINE"
    ENVIRONMENTAL_COVARIATE = "ENVIRONMENTAL_COVARIATE"
    CORRELATION_ANALYSIS = "CORRELATION_ANALYSIS"
    ANOMALY_CONTEXT = "ANOMALY_CONTEXT"
    POPULATION_NORMALIZATION = "POPULATION_NORMALIZATION"
    EVENT_COMPARISON = "EVENT_COMPARISON"


class StatisticalRelationship(StrEnum):
    CONTEXT_ONLY = "CONTEXT_ONLY"
    CORRELATION_ONLY_NOT_CAUSATION = "CORRELATION_ONLY_NOT_CAUSATION"


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude out of range")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude out of range")


@dataclass(frozen=True, slots=True)
class PopulationObservation:
    observation_id: str
    timestamp: datetime
    location: GeoPoint
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", require_aware_utc(self.timestamp))


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    weather_id: str
    timestamp: datetime
    location: GeoPoint
    evidence_class: EvidenceClass
    source_name: str
    source_origin: str
    source_capture_sha256: str
    temperature_c: float | None = None
    precipitation_mm: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_mps: float | None = None
    pressure_hpa: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", require_aware_utc(self.timestamp))
        if self.relative_humidity_pct is not None and not 0 <= self.relative_humidity_pct <= 100:
            raise ValueError("relative_humidity_pct out of range")
        if self.precipitation_mm is not None and self.precipitation_mm < 0:
            raise ValueError("precipitation_mm cannot be negative")
        if self.wind_speed_mps is not None and self.wind_speed_mps < 0:
            raise ValueError("wind_speed_mps cannot be negative")


@dataclass(frozen=True, slots=True)
class WeatherBinding:
    population_observation_id: str
    weather_id: str
    weather_evidence_class: EvidenceClass
    time_delta_seconds: float
    distance_km: float
    match_score: float
    relationship: StatisticalRelationship = StatisticalRelationship.CONTEXT_ONLY


@dataclass(frozen=True, slots=True)
class JoinedStatisticalContext:
    population: PopulationObservation
    weather: WeatherObservation
    binding: WeatherBinding

    @property
    def permitted_uses(self) -> tuple[WeatherUse, ...]:
        return tuple(WeatherUse)

    @property
    def asset_provenance(self) -> bool:
        return False

    @property
    def asset_authenticity(self) -> bool:
        return False

    @property
    def identity(self) -> bool:
        return False

    @property
    def authorization(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    population_metric: str
    weather_metric: str
    sample_count: int
    pearson_r: float | None
    relationship: StatisticalRelationship = StatisticalRelationship.CORRELATION_ONLY_NOT_CAUSATION


class WeatherStatisticsRail:
    logical_slot_count = ADOBE_LOGICAL_SLOT_COUNT
    version = FR0333_WEATHER_RAIL_VERSION

    def __init__(self, *, max_time_delta_seconds: float = 3600, max_distance_km: float = 50) -> None:
        if max_time_delta_seconds <= 0 or max_distance_km <= 0:
            raise ValueError("binding tolerances must be positive")
        self.max_time_delta_seconds = max_time_delta_seconds
        self.max_distance_km = max_distance_km

    def bind(self, population: PopulationObservation,
             weather_observations: Iterable[WeatherObservation]) -> JoinedStatisticalContext | None:
        candidates = []
        for weather in weather_observations:
            delta = abs((population.timestamp - weather.timestamp).total_seconds())
            distance = haversine_km(population.location, weather.location)
            if delta <= self.max_time_delta_seconds and distance <= self.max_distance_km:
                score = sqrt((delta / self.max_time_delta_seconds) ** 2 +
                             (distance / self.max_distance_km) ** 2)
                candidates.append((score, delta, distance, weather))
        if not candidates:
            return None
        score, delta, distance, selected = min(candidates, key=lambda item: item[0])
        return JoinedStatisticalContext(
            population,
            selected,
            WeatherBinding(
                population.observation_id,
                selected.weather_id,
                selected.evidence_class,
                delta,
                distance,
                score,
            ),
        )

    def bind_population(self, population: Iterable[PopulationObservation],
                        weather_observations: Iterable[WeatherObservation]) -> list[JoinedStatisticalContext]:
        weather = tuple(weather_observations)
        return [joined for observation in population if (joined := self.bind(observation, weather))]

    def correlation(self, contexts: Sequence[JoinedStatisticalContext], *,
                    population_metric: str, weather_metric: str) -> CorrelationResult:
        allowed = {"temperature_c", "precipitation_mm", "relative_humidity_pct",
                   "wind_speed_mps", "pressure_hpa"}
        if weather_metric not in allowed:
            raise ValueError("unsupported weather metric")
        pairs = [
            (context.population.values.get(population_metric), getattr(context.weather, weather_metric))
            for context in contexts
        ]
        valid = [(float(x), float(y)) for x, y in pairs if x is not None and y is not None]
        return CorrelationResult(
            population_metric,
            weather_metric,
            len(valid),
            pearson_correlation([x for x, _ in valid], [y for _, y in valid]),
        )


def pearson_correlation(x_values: Sequence[float], y_values: Sequence[float]) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError("length mismatch")
    if len(x_values) < 2:
        return None
    mean_x, mean_y = fmean(x_values), fmean(y_values)
    dx, dy = [x - mean_x for x in x_values], [y - mean_y for y in y_values]
    denominator = sqrt(sum(x * x for x in dx)) * sqrt(sum(y * y for y in dy))
    return None if denominator == 0 else sum(x * y for x, y in zip(dx, dy, strict=True)) / denominator


def haversine_km(first: GeoPoint, second: GeoPoint) -> float:
    radius = 6371.0088
    lat1, lon1, lat2, lon2 = map(radians, (first.latitude, first.longitude,
                                           second.latitude, second.longitude))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(value))


def export_statistical_context(context: JoinedStatisticalContext) -> dict[str, object]:
    return {
        "rail": "FR0333.WEATHER.STATISTICS.RAIL",
        "version": FR0333_WEATHER_RAIL_VERSION,
        "adobe_logical_slot_count": ADOBE_LOGICAL_SLOT_COUNT,
        "population_observation": asdict(context.population),
        "weather_observation": asdict(context.weather),
        "binding": asdict(context.binding),
        "permitted_uses": [use.value for use in context.permitted_uses],
        "prohibited_predicates": {
            "asset_provenance": True,
            "asset_authenticity": True,
            "identity": True,
            "authorization": True,
            "causation": True,
        },
        "relationship": StatisticalRelationship.CONTEXT_ONLY.value,
    }


def require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
