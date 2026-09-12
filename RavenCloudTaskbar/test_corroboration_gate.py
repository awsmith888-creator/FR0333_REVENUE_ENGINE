import unittest

from corroboration_gate import CorroborationError, REQUIRED_FIELDS, validate_claim


def claim(state="C1", sources=None, promotion="AUTHENTICITY_ONLY",
          contradiction="NOT_RUN", causation="NOT_RUN"):
    return {
        "CLAIM.ID": "TEST.CLAIM",
        "SOURCE.ORIGIN": "ORIGIN.A" if state != "C0" else "UNKNOWN",
        "SOURCE.DERIVATION": "ORIGINAL",
        "SOURCE.INDEPENDENCE": "PRESENT" if state in {"C3", "C4", "C5", "C6"} else "NOT_DEMONSTRATED",
        "SOURCE.CLASS": "FIRSTHAND",
        "CLAIM.CLASS": "ALLEGATION",
        "CORROBORATION.STATE": state,
        "CONTRADICTION.STATE": contradiction,
        "CAUSATION.STATE": causation,
        "PROMOTION.STATE": promotion,
        "SOURCES": sources or [{"source_id": "S1", "origin": "ORIGIN.A", "derivation": "ORIGINAL"}],
    }


class CorroborationKernelTests(unittest.TestCase):
    def test_k1_ten_headlines_one_origin_remain_one_origin(self):
        sources = [
            {"source_id": f"REPORT.{i}", "origin": "LIVESTREAM.1", "derivation": "DERIVED"}
            for i in range(10)
        ]
        receipt = validate_claim(claim("C2", sources=sources))
        self.assertEqual(receipt["report_count"], 10)
        self.assertEqual(receipt["evidentiary_origin_count"], 1)
        self.assertEqual(receipt["corroboration_state"], "C2")

    def test_k2_c2_cannot_promote_as_fact(self):
        sources = [
            {"source_id": "R1", "origin": "CLIP.1", "derivation": "DERIVED"},
            {"source_id": "R2", "origin": "CLIP.1", "derivation": "DERIVED"},
        ]
        with self.assertRaisesRegex(CorroborationError, "AUTHENTICITY_NE_TRUTH"):
            validate_claim(claim("C2", sources=sources, promotion="FACT"))

    def test_k3_independent_testimony_requires_second_origin(self):
        with self.assertRaisesRegex(CorroborationError, "INDEPENDENCE_NOT_DEMONSTRATED"):
            validate_claim(claim("C3"))

    def test_k4_independent_documentary_evidence_passes(self):
        sources = [
            {"source_id": "W1", "origin": "WITNESS.1", "derivation": "ORIGINAL"},
            {"source_id": "D1", "origin": "CONTRACT.1", "derivation": "ORIGINAL"},
        ]
        receipt = validate_claim(
            claim("C4", sources=sources, promotion="INDEPENDENT_CORROBORATION_PRESENT")
        )
        self.assertEqual(receipt["evidentiary_origin_count"], 2)

    def test_k5_c6_higher_confidence_requires_contradiction_pass(self):
        sources = [
            {"source_id": "W1", "origin": "WITNESS.1", "derivation": "ORIGINAL"},
            {"source_id": "D1", "origin": "DATASET.1", "derivation": "ORIGINAL"},
        ]
        with self.assertRaisesRegex(CorroborationError, "CONTRADICTION_PASS"):
            validate_claim(
                claim("C6", sources=sources,
                      promotion="HIGHER_EVIDENTIARY_CONFIDENCE",
                      contradiction="UNRESOLVED")
            )
        receipt = validate_claim(
            claim("C6", sources=sources,
                  promotion="HIGHER_EVIDENTIARY_CONFIDENCE",
                  contradiction="PASS")
        )
        self.assertEqual(receipt["gate"], "PASS")

    def test_k6_corroboration_ne_causation(self):
        sources = [
            {"source_id": "W1", "origin": "WITNESS.1", "derivation": "ORIGINAL"},
            {"source_id": "D1", "origin": "DATASET.1", "derivation": "ORIGINAL"},
        ]
        with self.assertRaisesRegex(CorroborationError, "CAUSAL_GATE_REQUIRED"):
            validate_claim(
                claim("C6", sources=sources, promotion="CAUSAL",
                      contradiction="PASS", causation="NOT_RUN")
            )

    def test_all_nine_lineage_fields_are_mandatory(self):
        self.assertEqual(len(REQUIRED_FIELDS), 9)
        for field in REQUIRED_FIELDS:
            item = claim()
            del item[field]
            with self.subTest(field=field):
                with self.assertRaisesRegex(CorroborationError, "LINEAGE_FIELDS_REQUIRED"):
                    validate_claim(item)


if __name__ == "__main__":
    unittest.main()
