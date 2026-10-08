from __future__ import annotations

from typing import Any


POLICY_ID = "FR0333.M365.INTENT.GATE.REVIEW.POLICY.0001"


def evaluate_review_policy(
    *,
    local_verification_pass: bool,
    authenticated_runtime_established: bool,
    external_execution_count: int,
    provider_envelope_count: int,
    humanlock_active: bool,
) -> dict[str, Any]:
    """Deterministic review gate for local-vs-runtime evidence boundaries.

    This gate intentionally never auto-approves, marks ready, or merges a PR.
    Local fixture success may justify a non-approving review comment only.
    Authenticated runtime evidence is a prerequisite for any later promotion,
    and even then a human review remains required.
    """
    if external_execution_count < 0 or provider_envelope_count < 0:
        raise ValueError("counts must be non-negative")

    boundary_breach = (
        not authenticated_runtime_established
        and (external_execution_count > 0 or provider_envelope_count > 0)
    )

    if boundary_breach:
        return {
            "POLICY.ID": POLICY_ID,
            "DECISION": "REJECT",
            "CONSEQUENCE": "C.9.BOUNDARY.BREACH",
            "LOCAL.VERIFICATION": "PASS" if local_verification_pass else "HOLD",
            "AUTHENTICATED.RUNTIME": "NOT.ESTABLISHED",
            "EXTERNAL.EXECUTION.STATE": "REJECT",
            "REVIEW.ACTION": "REQUEST.CHANGES",
            "APPROVE.ALLOWED": False,
            "READY.ALLOWED": False,
            "MERGE.ALLOWED": False,
            "AUTO.PROMOTION.ALLOWED": False,
        }

    if not local_verification_pass:
        return {
            "POLICY.ID": POLICY_ID,
            "DECISION": "HOLD",
            "CONSEQUENCE": None,
            "LOCAL.VERIFICATION": "HOLD",
            "AUTHENTICATED.RUNTIME": (
                "ESTABLISHED" if authenticated_runtime_established else "NOT.ESTABLISHED"
            ),
            "EXTERNAL.EXECUTION.STATE": "HOLD",
            "REVIEW.ACTION": "COMMENT.ONLY",
            "APPROVE.ALLOWED": False,
            "READY.ALLOWED": False,
            "MERGE.ALLOWED": False,
            "AUTO.PROMOTION.ALLOWED": False,
        }

    if not authenticated_runtime_established:
        return {
            "POLICY.ID": POLICY_ID,
            "DECISION": "PASS.LOCAL.HOLD.EXTERNAL",
            "CONSEQUENCE": None,
            "LOCAL.VERIFICATION": "PASS",
            "AUTHENTICATED.RUNTIME": "NOT.ESTABLISHED",
            "EXTERNAL.EXECUTION.STATE": "HOLD",
            "REVIEW.ACTION": "COMMENT.ONLY",
            "REVIEW.COMMENT": (
                "exact-head local fixture verification accepted; "
                "authenticated runtime remains unestablished"
            ),
            "APPROVE.ALLOWED": False,
            "READY.ALLOWED": False,
            "MERGE.ALLOWED": False,
            "AUTO.PROMOTION.ALLOWED": False,
            "REQUIRED.NEXT.EVIDENCE": "AUTHENTICATED.RUNTIME.RECEIPT",
        }

    return {
        "POLICY.ID": POLICY_ID,
        "DECISION": "HOLD.HUMAN.REVIEW" if humanlock_active else "HOLD.HUMAN.REVIEW",
        "CONSEQUENCE": None,
        "LOCAL.VERIFICATION": "PASS",
        "AUTHENTICATED.RUNTIME": "ESTABLISHED",
        "EXTERNAL.EXECUTION.STATE": "HOLD.HUMAN.REVIEW",
        "REVIEW.ACTION": "HUMAN.REVIEW.REQUIRED",
        "APPROVE.ALLOWED": False,
        "READY.ALLOWED": False,
        "MERGE.ALLOWED": False,
        "AUTO.PROMOTION.ALLOWED": False,
    }
