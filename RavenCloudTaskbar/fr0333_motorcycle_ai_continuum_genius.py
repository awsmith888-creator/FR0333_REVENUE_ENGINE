#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "fr0333_motorcycle_ai_continuum_matrix_0001.json"
INDEX_PATH = ROOT / "fr0333_golden_chain_index_0001.json"

EXPECTED_PREFIX = [
    "0.1.FR.0333.GOLDEN.CHAIN.ANDALUSIA.0001",
    "0.2.FR.0333.GOLDEN.CHAIN.CENSUS.BLACK.DETAILED.ORIGIN.0001",
    "0.3.FR.0333.GOLDEN.CHAIN.TWO.LANE.HIGHWAY.0001",
    "0.4.FR.0333.GOLDEN.CHAIN.RED.SEA.DUAL.CHOKEPOINT.0001",
]
EXPECTED_05 = "0.5.FR.0333.GOLDEN.CHAIN.MOTORCYCLE.AI.CONTINUUM.0001"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    spec = load(SPEC_PATH)
    index = load(INDEX_PATH)

    assert spec["id"] == "FR0333.MOTORCYCLE.AI.CONTINUUM.MATRIX.0001"
    assert spec["golden_chain_position"] == "0.5"
    assert spec["golden_chain_identifier"] == "FR.0333.GOLDEN.CHAIN.MOTORCYCLE.AI.CONTINUUM.0001"
    assert spec["deployment_state"] == "GOLDEN_CHAIN.INDEX.ACTIVE"
    assert spec["runtime"] == "NOT.APPLICABLE.SPECIFICATION.INDEX"
    assert spec["evidence_classes"]["future_ai_growth"] == "UNVERIFIED.FUTURE.CLAIM.HOLD"

    laws = set(spec["ai_continuum"]["controlling_laws"])
    assert "MODEL.INSTANCE.SELF.MODIFICATION = FALSE" in laws
    assert "CURRENT.TREND != GUARANTEED.FUTURE.RATE" in laws

    public_index = index["public_index"]
    assert public_index[:4] == EXPECTED_PREFIX
    assert public_index[4] == EXPECTED_05
    assert len(public_index) == len(set(public_index))

    entries = index["entries"]
    positions = [row["index"] for row in entries]
    identifiers = [row["identifier"] for row in entries]
    assert len(positions) == len(set(positions))
    assert len(identifiers) == len(set(identifiers))

    row = next(row for row in entries if row["index"] == "0.5")
    assert row["artifact"] == "RavenCloudTaskbar/fr0333_motorcycle_ai_continuum_matrix_0001.json"
    assert "INDEXED" in row["state"]

    return {
        "result": "T.20.PASS",
        "spec": spec["id"],
        "golden_chain_position": "0.5",
        "runtime_claim": "NONE",
        "future_claim_state": "U.21.HOLD",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
