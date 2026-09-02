import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fr0333_weather_persistence import WeatherBindingStore
from fr0333_weather_statistics import (
    ADOBE_LOGICAL_SLOT_COUNT,
    EvidenceClass,
    GeoPoint,
    PopulationObservation,
    StatisticalRelationship,
    WeatherObservation,
    WeatherStatisticsRail,
    export_statistical_context,
)


def fixtures():
    moment = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    population = PopulationObservation(
        "POP.1", moment, GeoPoint(40.9153, -81.1059), {"event_count": 7}
    )
    weather = WeatherObservation(
        "WX.1",
        moment + timedelta(minutes=5),
        GeoPoint(40.9200, -81.1000),
        EvidenceClass.E_MES,
        "GOOGLE.WEATHER",
        "GOOGLE.SEARCH.HELP",
        "a" * 64,
        temperature_c=24.0,
        precipitation_mm=0.0,
    )
    return population, weather


class WeatherRailTests(unittest.TestCase):
    def test_slot_count_remains_64(self):
        self.assertEqual(ADOBE_LOGICAL_SLOT_COUNT, 64)
        self.assertEqual(WeatherStatisticsRail.logical_slot_count, 64)

    def test_binding_is_location_timestamp_bounded(self):
        population, weather = fixtures()
        joined = WeatherStatisticsRail(
            max_time_delta_seconds=600, max_distance_km=5
        ).bind(population, [weather])
        self.assertIsNotNone(joined)
        self.assertLessEqual(joined.binding.time_delta_seconds, 600)
        self.assertLessEqual(joined.binding.distance_km, 5)

    def test_out_of_tolerance_weather_is_not_bound(self):
        population, weather = fixtures()
        self.assertIsNone(
            WeatherStatisticsRail(max_time_delta_seconds=30).bind(population, [weather])
        )

    def test_weather_can_never_satisfy_asset_predicates(self):
        population, weather = fixtures()
        context = WeatherStatisticsRail().bind(population, [weather])
        self.assertFalse(context.asset_provenance)
        self.assertFalse(context.asset_authenticity)
        self.assertFalse(context.identity)
        self.assertFalse(context.authorization)

    def test_export_has_no_positive_asset_assertions(self):
        population, weather = fixtures()
        exported = export_statistical_context(
            WeatherStatisticsRail().bind(population, [weather])
        )
        self.assertEqual(exported["adobe_logical_slot_count"], 64)
        self.assertEqual(exported["relationship"], "CONTEXT_ONLY")
        self.assertTrue(all(exported["prohibited_predicates"].values()))

    def test_correlation_is_labeled_not_causation(self):
        population, weather = fixtures()
        rail = WeatherStatisticsRail()
        context = rail.bind(population, [weather])
        result = rail.correlation(
            [context], population_metric="event_count", weather_metric="temperature_c"
        )
        self.assertEqual(
            result.relationship,
            StatisticalRelationship.CORRELATION_ONLY_NOT_CAUSATION,
        )

    def test_persistence_forces_all_asset_predicates_to_zero(self):
        population, weather = fixtures()
        context = WeatherStatisticsRail().bind(population, [weather])
        with tempfile.TemporaryDirectory() as directory:
            store = WeatherBindingStore(Path(directory) / "weather.sqlite3")
            receipt = store.persist(context)
            row = store.binding("POP.1", "WX.1")
            self.assertEqual(receipt["adobe_logical_slot_count"], 64)
            for field in (
                "asset_provenance",
                "asset_authenticity",
                "identity",
                "authorization",
                "causation",
            ):
                self.assertEqual(row[field], 0)

    def test_database_rejects_weather_as_provenance(self):
        population, weather = fixtures()
        context = WeatherStatisticsRail().bind(population, [weather])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.sqlite3"
            store = WeatherBindingStore(path)
            store.persist(context)
            with sqlite3.connect(path) as connection:
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """UPDATE weather_bindings SET asset_provenance=1
                           WHERE population_observation_id='POP.1'"""
                    )

    def test_weather_source_provenance_stays_inside_weather_table(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WeatherBindingStore(Path(directory) / "weather.sqlite3")
            weather_columns = store.schema_columns("weather_observations")
            binding_columns = store.schema_columns("weather_bindings")
            self.assertIn("source_origin", weather_columns)
            self.assertNotIn("source_origin", binding_columns)
            self.assertNotIn("asset_id", weather_columns)

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            PopulationObservation(
                "POP.BAD", datetime(2026, 9, 2, 10, 0), GeoPoint(0, 0), {}
            )


if __name__ == "__main__":
    unittest.main()
