import sqlite3
import unittest
from datetime import datetime, timezone

from RavenCloudTaskbar.fr0333_weather_statistics import (
    ADOBE_LOGICAL_SLOT_COUNT,
    EvidenceClass,
    GeoPoint,
    PopulationObservation,
    StatisticalRelationship,
    WeatherBindingStore,
    WeatherObservation,
    WeatherStatisticsRail,
    export_statistical_context,
)


class WeatherStatisticsRailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.population = PopulationObservation(
            observation_id="POP-001",
            timestamp=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            location=GeoPoint(40.8373, -81.2596),
            values={"event_count": 10.0},
        )
        self.weather = WeatherObservation(
            weather_id="WX-001",
            timestamp=datetime(2026, 9, 2, 12, 10, tzinfo=timezone.utc),
            location=GeoPoint(40.8373, -81.2596),
            evidence_class=EvidenceClass.E_OBS,
            source_name="TEST_SOURCE",
            temperature_c=20.0,
            relative_humidity_pct=50.0,
        )
        self.rail = WeatherStatisticsRail(
            max_time_delta_seconds=3600.0,
            max_distance_km=50.0,
        )

    def _context(self):
        context = self.rail.bind(self.population, [self.weather])
        self.assertIsNotNone(context)
        return context

    def test_weather_does_not_create_slot_65(self) -> None:
        self.assertEqual(ADOBE_LOGICAL_SLOT_COUNT, 64)
        self.assertEqual(self.rail.logical_slot_count, 64)

    def test_weather_never_satisfies_asset_predicates(self) -> None:
        context = self._context()
        self.assertFalse(context.asset_provenance)
        self.assertFalse(context.asset_authenticity)
        self.assertFalse(context.identity)
        self.assertFalse(context.authorization)

    def test_export_contains_no_positive_asset_predicate(self) -> None:
        exported = export_statistical_context(self._context())
        governing = exported["governing_law"]
        self.assertTrue(governing["weather_ne_provenance"])
        self.assertTrue(governing["weather_ne_authenticity"])
        self.assertTrue(governing["weather_ne_identity"])
        self.assertTrue(governing["weather_ne_authorization"])
        self.assertNotIn("asset_provenance", exported)
        self.assertNotIn("asset_authenticity", exported)
        self.assertNotIn("identity", exported)
        self.assertNotIn("authorization", exported)

    def test_binding_is_context_only(self) -> None:
        context = self._context()
        self.assertEqual(
            context.binding.relationship,
            StatisticalRelationship.CONTEXT_ONLY,
        )

    def test_correlation_is_labeled_not_causation(self) -> None:
        second_population = PopulationObservation(
            observation_id="POP-002",
            timestamp=datetime(2026, 9, 2, 13, 0, tzinfo=timezone.utc),
            location=GeoPoint(40.8373, -81.2596),
            values={"event_count": 20.0},
        )
        second_weather = WeatherObservation(
            weather_id="WX-002",
            timestamp=datetime(2026, 9, 2, 13, 5, tzinfo=timezone.utc),
            location=GeoPoint(40.8373, -81.2596),
            evidence_class=EvidenceClass.E_MES,
            source_name="TEST_SOURCE",
            temperature_c=25.0,
        )
        contexts = self.rail.bind_population(
            [self.population, second_population],
            [self.weather, second_weather],
        )
        result = self.rail.correlation(
            contexts,
            population_metric="event_count",
            weather_metric="temperature_c",
        )
        self.assertEqual(
            result.relationship,
            StatisticalRelationship.CORRELATION_ONLY_NOT_CAUSATION,
        )

    def test_persistence_schema_has_no_asset_provenance_columns(self) -> None:
        connection = sqlite3.connect(":memory:")
        store = WeatherBindingStore(connection)
        store.initialize()
        store.persist(self._context())

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(fr0333_weather_bindings)"
            ).fetchall()
        }
        forbidden = {
            "asset_provenance",
            "asset_authenticity",
            "identity",
            "authorization",
        }
        self.assertTrue(forbidden.isdisjoint(columns))

        row = connection.execute(
            "SELECT relationship, weather_evidence_class, rail_version "
            "FROM fr0333_weather_bindings"
        ).fetchone()
        self.assertEqual(row[0], "CONTEXT_ONLY")
        self.assertEqual(row[1], "E_OBS")
        self.assertEqual(row[2], "1.0.5-FINAL")


if __name__ == "__main__":
    unittest.main()
