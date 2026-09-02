from __future__ import annotations

import json
import sqlite3
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
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True, slots=True)
class PopulationObservation:
    observation_id: str
    timestamp: datetime
    location: GeoPoint
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _require_aware_utc(self.timestamp))


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    weather_id: str
    timestamp: datetime
    location: GeoPoint
    evidence_class: EvidenceClass
    source_name: str
    temperature_c: float | None = None
    precipitation_mm: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_mps: float | None = None
    pressure_hpa: float | None = None
    condition_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _require_aware_utc(self.timestamp))
        if self.relative_humidity_pct is not None and not 0.0 <= self.relative_humidity_pct <= 100.0:
            raise ValueError("relative_humidity_pct must be between 0 and 100")
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
    """FR0333.WEATHER.STATISTICS.RAIL external statistical-context sidecar."""

    logical_slot_count = ADOBE_LOGICAL_SLOT_COUNT
    version = FR0333_WEATHER_RAIL_VERSION

    def __init__(self, *, max_time_delta_seconds: float = 3600.0, max_distance_km: float = 50.0) -> None:
        if max_time_delta_seconds <= 0:
            raise ValueError("max_time_delta_seconds must be positive")
        if max_distance_km <= 0:
            raise ValueError("max_distance_km must be positive")
        self.max_time_delta_seconds = max_time_delta_seconds
        self.max_distance_km = max_distance_km

    def bind(self, population: PopulationObservation, weather_observations: Iterable[WeatherObservation]) -> JoinedStatisticalContext | None:
        best_weather: WeatherObservation | None = None
        best_distance = 0.0
        best_time_delta = 0.0
        best_score = float("inf")
        for weather in weather_observations:
            time_delta = abs((population.timestamp - weather.timestamp).total_seconds())
            if time_delta > self.max_time_delta_seconds:
                continue
            distance = haversine_km(population.location, weather.location)
            if distance > self.max_distance_km:
                continue
            score = self._match_score(time_delta_seconds=time_delta, distance_km=distance)
            if score < best_score:
                best_weather = weather
                best_distance = distance
                best_time_delta = time_delta
                best_score = score
        if best_weather is None:
            return None
        binding = WeatherBinding(
            population_observation_id=population.observation_id,
            weather_id=best_weather.weather_id,
            weather_evidence_class=best_weather.evidence_class,
            time_delta_seconds=best_time_delta,
            distance_km=best_distance,
            match_score=best_score,
        )
        return JoinedStatisticalContext(population=population, weather=best_weather, binding=binding)

    def bind_population(self, population: Iterable[PopulationObservation], weather_observations: Iterable[WeatherObservation]) -> list[JoinedStatisticalContext]:
        weather = tuple(weather_observations)
        return [context for observation in population if (context := self.bind(observation, weather)) is not None]

    def correlation(self, contexts: Sequence[JoinedStatisticalContext], *, population_metric: str, weather_metric: str) -> CorrelationResult:
        valid_weather_metrics = {
            "temperature_c", "precipitation_mm", "relative_humidity_pct", "wind_speed_mps", "pressure_hpa"
        }
        if weather_metric not in valid_weather_metrics:
            raise ValueError(f"Unsupported weather metric: {weather_metric}. Expected one of {sorted(valid_weather_metrics)}")
        x_values: list[float] = []
        y_values: list[float] = []
        for context in contexts:
            population_value = context.population.values.get(population_metric)
            weather_value = getattr(context.weather, weather_metric)
            if population_value is None or weather_value is None:
                continue
            x_values.append(float(population_value))
            y_values.append(float(weather_value))
        return CorrelationResult(
            population_metric=population_metric,
            weather_metric=weather_metric,
            sample_count=len(x_values),
            pearson_r=pearson_correlation(x_values, y_values),
        )

    def _match_score(self, *, time_delta_seconds: float, distance_km: float) -> float:
        temporal_component = time_delta_seconds / self.max_time_delta_seconds
        spatial_component = distance_km / self.max_distance_km
        return sqrt(temporal_component**2 + spatial_component**2)


WEATHER_BINDING_DDL = """
CREATE TABLE IF NOT EXISTS fr0333_weather_bindings (
    population_observation_id TEXT NOT NULL,
    weather_id TEXT NOT NULL,
    weather_evidence_class TEXT NOT NULL CHECK (weather_evidence_class IN ('E_OBS','E_MES')),
    population_timestamp_utc TEXT NOT NULL,
    weather_timestamp_utc TEXT NOT NULL,
    population_latitude REAL NOT NULL,
    population_longitude REAL NOT NULL,
    weather_latitude REAL NOT NULL,
    weather_longitude REAL NOT NULL,
    weather_source_name TEXT NOT NULL,
    time_delta_seconds REAL NOT NULL CHECK (time_delta_seconds >= 0),
    distance_km REAL NOT NULL CHECK (distance_km >= 0),
    match_score REAL NOT NULL CHECK (match_score >= 0),
    relationship TEXT NOT NULL CHECK (relationship IN ('CONTEXT_ONLY','CORRELATION_ONLY_NOT_CAUSATION')),
    population_values_json TEXT NOT NULL,
    weather_values_json TEXT NOT NULL,
    rail_version TEXT NOT NULL,
    PRIMARY KEY (population_observation_id, weather_id)
);
"""


class WeatherBindingStore:
    """Persistence is statistical-context only; no asset provenance/authenticity predicates exist in this schema."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(WEATHER_BINDING_DDL)
        self.connection.commit()

    def persist(self, context: JoinedStatisticalContext) -> None:
        weather_values = {
            "temperature_c": context.weather.temperature_c,
            "precipitation_mm": context.weather.precipitation_mm,
            "relative_humidity_pct": context.weather.relative_humidity_pct,
            "wind_speed_mps": context.weather.wind_speed_mps,
            "pressure_hpa": context.weather.pressure_hpa,
            "condition_code": context.weather.condition_code,
        }
        self.connection.execute(
            """
            INSERT OR REPLACE INTO fr0333_weather_bindings (
                population_observation_id, weather_id, weather_evidence_class,
                population_timestamp_utc, weather_timestamp_utc,
                population_latitude, population_longitude,
                weather_latitude, weather_longitude, weather_source_name,
                time_delta_seconds, distance_km, match_score, relationship,
                population_values_json, weather_values_json, rail_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                context.population.observation_id,
                context.weather.weather_id,
                context.weather.evidence_class.value,
                context.population.timestamp.isoformat(),
                context.weather.timestamp.isoformat(),
                context.population.location.latitude,
                context.population.location.longitude,
                context.weather.location.latitude,
                context.weather.location.longitude,
                context.weather.source_name,
                context.binding.time_delta_seconds,
                context.binding.distance_km,
                context.binding.match_score,
                context.binding.relationship.value,
                json.dumps(dict(context.population.values), sort_keys=True, separators=(",", ":")),
                json.dumps(weather_values, sort_keys=True, separators=(",", ":")),
                FR0333_WEATHER_RAIL_VERSION,
            ),
        )
        self.connection.commit()


def pearson_correlation(x_values: Sequence[float], y_values: Sequence[float]) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError("x_values and y_values must have equal lengths")
    if len(x_values) < 2:
        return None
    mean_x = fmean(x_values)
    mean_y = fmean(y_values)
    deviations_x = [value - mean_x for value in x_values]
    deviations_y = [value - mean_y for value in y_values]
    denominator_x = sqrt(sum(value**2 for value in deviations_x))
    denominator_y = sqrt(sum(value**2 for value in deviations_y))
    denominator = denominator_x * denominator_y
    if denominator == 0:
        return None
    numerator = sum(x_delta * y_delta for x_delta, y_delta in zip(deviations_x, deviations_y, strict=True))
    return numerator / denominator


def haversine_km(first: GeoPoint, second: GeoPoint) -> float:
    earth_radius_km = 6371.0088
    lat1 = radians(first.latitude)
    lon1 = radians(first.longitude)
    lat2 = radians(second.latitude)
    lon2 = radians(second.longitude)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    haversine = sin(delta_lat / 2.0) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2.0) ** 2
    return 2.0 * earth_radius_km * asin(sqrt(haversine))


def export_statistical_context(context: JoinedStatisticalContext) -> dict[str, object]:
    return {
        "rail": "FR0333.WEATHER.STATISTICS.RAIL",
        "version": FR0333_WEATHER_RAIL_VERSION,
        "adobe_logical_slot_count": ADOBE_LOGICAL_SLOT_COUNT,
        "population_observation": asdict(context.population),
        "weather_observation": asdict(context.weather),
        "binding": asdict(context.binding),
        "permitted_uses": [permitted_use.value for permitted_use in context.permitted_uses],
        "governing_law": {
            "asset_evidence_ne_environmental_context": True,
            "environmental_context_ne_statistical_relationship": True,
            "statistical_relationship_ne_causation": True,
            "weather_ne_provenance": True,
            "weather_ne_authenticity": True,
            "weather_ne_identity": True,
            "weather_ne_authorization": True,
            "weather_correlation_ne_causation": True,
        },
    }


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
