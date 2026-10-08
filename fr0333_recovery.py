"""FR0333 predictive lane recovery. No external side effects or automatic promotion."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

class State(str, Enum):
    GREEN = "T.20"
    YELLOW = "U.21"
    RED = "F.6"

class Routing(str, Enum):
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"

@dataclass
class Lane:
    lane_id: str
    partner_id: str
    state: State = State.YELLOW
    routing: Routing = Routing.ACTIVE
    evidence: List[str] = field(default_factory=list)

@dataclass
class Receipt:
    source: str
    replacement: Optional[str]
    state: State
    reason: str
    bloom: str

class RecoveryController:
    """Preserves 64 paired rails; MR.00 supervises and is never a lane."""
    def __init__(self):
        self.active: Dict[str, Lane] = {}
        self.passive: Dict[str, Lane] = {}
        for n in range(1, 65):
            a, p = f"A.{n:02d}", f"P.{n:02d}"
            self.active[a] = Lane(a, p)
            self.passive[p] = Lane(p, a)
        self.receipts: List[Receipt] = []
        self.blooms: List[dict] = []
        self.supervisor = "MR.00"

    def observe(self, lane_id: str, passed: bool, evidence: str) -> None:
        lane = self._lane(lane_id)
        if not evidence.strip():
            raise ValueError("Evidence required")
        lane.evidence.append(evidence)
        if not passed:
            lane.state = State.RED
            lane.routing = Routing.QUARANTINED
        elif lane.routing == Routing.ACTIVE:
            lane.state = State.GREEN

    def _lane(self, lane_id: str) -> Lane:
        lanes = self.active if lane_id.startswith("A.") else self.passive
        return lanes[lane_id]

    def recover(self, failed_id: str, candidates: List[str], test) -> Receipt:
        failed = self._lane(failed_id)
        if failed.state != State.RED or failed.routing != Routing.QUARANTINED:
            raise ValueError("Only quarantined failed lanes can be rerouted")
        for candidate_id in candidates:
            if candidate_id == failed_id:
                continue
            candidate = self._lane(candidate_id)
            partner = self._lane(candidate.partner_id)
            if candidate.routing != Routing.ACTIVE or candidate.state != State.GREEN:
                continue
            if partner.routing != Routing.ACTIVE or partner.state != State.GREEN:
                continue
            # An external, deterministic regression function verifies the candidate.
            if not test(candidate_id):
                self.blooms.append({"lane": candidate_id, "state": "FAILED.BLOOM", "reason": "regression failed"})
                continue
            receipt = Receipt(failed_id, candidate_id, State.GREEN, "verified alternate route", "HOLD.BLOOM")
            self.receipts.append(receipt)
            self.blooms.append({"lane": failed_id, "state": "HOLD.BLOOM", "replacement": candidate_id})
            return receipt
        receipt = Receipt(failed_id, None, State.YELLOW, "no verified alternate route", "HOLD.BLOOM")
        self.receipts.append(receipt)
        return receipt

    def retire(self, lane_id: str, humanlock_approved: bool) -> None:
        if not humanlock_approved:
            raise PermissionError("HUMANLOCK approval required")
        lane = self._lane(lane_id)
        if lane.routing != Routing.QUARANTINED:
            raise ValueError("Retire only after quarantine")
        lane.routing = Routing.RETIRED
        # Diagnostic failure state and evidence are retained.
