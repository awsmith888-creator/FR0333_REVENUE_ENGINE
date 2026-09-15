from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from RavenCloudTaskbar.fr0333_weather_statistics import (
    JoinedStatisticalContext,
    export_statistical_context,
)


class WeatherBindingStore:
    """Persistence isolated from asset evidence and the 64-slot register."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS weather_observations (
                    weather_id TEXT PRIMARY KEY,
                    observed_at_utc TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    evidence_class TEXT NOT NULL CHECK(evidence_class IN ('E_OBS','E_MES')),
                    source_name TEXT NOT NULL,
                    source_origin TEXT NOT NULL,
                    source_capture_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS weather_bindings (
                    population_observation_id TEXT NOT NULL,
                    weather_id TEXT NOT NULL,
                    time_delta_seconds REAL NOT NULL,
                    distance_km REAL NOT NULL,
                    match_score REAL NOT NULL,
                    relationship TEXT NOT NULL CHECK(relationship='CONTEXT_ONLY'),
                    asset_provenance INTEGER NOT NULL DEFAULT 0 CHECK(asset_provenance=0),
                    asset_authenticity INTEGER NOT NULL DEFAULT 0 CHECK(asset_authenticity=0),
                    identity INTEGER NOT NULL DEFAULT 0 CHECK(identity=0),
                    authorization INTEGER NOT NULL DEFAULT 0 CHECK(authorization=0),
                    causation INTEGER NOT NULL DEFAULT 0 CHECK(causation=0),
                    PRIMARY KEY(population_observation_id, weather_id),
                    FOREIGN KEY(weather_id) REFERENCES weather_observations(weather_id)
                );
                """
            )

    def persist(self, context: JoinedStatisticalContext) -> dict[str, object]:
        exported = export_statistical_context(context)
        weather = context.weather
        binding = context.binding
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO weather_observations
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    weather.weather_id,
                    weather.timestamp.isoformat(),
                    weather.location.latitude,
                    weather.location.longitude,
                    weather.evidence_class.value,
                    weather.source_name,
                    weather.source_origin,
                    weather.source_capture_sha256,
                    json.dumps(exported["weather_observation"], sort_keys=True, default=str),
                ),
            )
            connection.execute(
                """INSERT OR REPLACE INTO weather_bindings
                   (population_observation_id, weather_id, time_delta_seconds,
                    distance_km, match_score, relationship)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    binding.population_observation_id,
                    binding.weather_id,
                    binding.time_delta_seconds,
                    binding.distance_km,
                    binding.match_score,
                    binding.relationship.value,
                ),
            )
        return {
            "state": "PERSISTED",
            "population_observation_id": binding.population_observation_id,
            "weather_id": binding.weather_id,
            "relationship": binding.relationship.value,
            "adobe_logical_slot_count": exported["adobe_logical_slot_count"],
        }

    def binding(self, population_observation_id: str, weather_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM weather_bindings
                   WHERE population_observation_id=? AND weather_id=?""",
                (population_observation_id, weather_id),
            ).fetchone()
        return dict(row) if row else None

    def schema_columns(self, table: str) -> set[str]:
        if table not in {"weather_observations", "weather_bindings"}:
            raise ValueError("unsupported table")
        with self._connect() as connection:
            return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
