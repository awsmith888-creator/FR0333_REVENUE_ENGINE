use serde::Serialize;

pub const BASIS_POINTS_SCALE: u64 = 10_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EvidenceState {
    Verified,
    Observed,
    Hold,
    Failed,
    NotObserved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum GateTarget {
    Staging,
    Publicity,
    Merge,
    Production,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CompatibilityCheck {
    pub id: String,
    pub state: EvidenceState,
    pub weight: u16,
    pub targets: Vec<GateTarget>,
    pub basis: String,
}

impl CompatibilityCheck {
    pub fn new(
        id: impl Into<String>,
        state: EvidenceState,
        targets: Vec<GateTarget>,
        basis: impl Into<String>,
    ) -> Self {
        Self {
            id: id.into(),
            state,
            weight: 100,
            targets,
            basis: basis.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct GeniusStatistics {
    pub total_checks: u64,
    pub verified_checks: u64,
    pub observed_checks: u64,
    pub hold_checks: u64,
    pub failed_checks: u64,
    pub not_observed_checks: u64,
    pub evidence_coverage_bps: u64,
    pub verified_alignment_bps: u64,
    pub weighted_alignment_bps: u64,
    pub probability_claimed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ReleaseGates {
    pub staging_ready: bool,
    pub publicity_ready: bool,
    pub merge_ready: bool,
    pub production_ready: bool,
}

pub fn calculate_statistics(checks: &[CompatibilityCheck]) -> GeniusStatistics {
    let total_checks = checks.len() as u64;
    let verified_checks = count_state(checks, EvidenceState::Verified);
    let observed_checks = count_state(checks, EvidenceState::Observed);
    let hold_checks = count_state(checks, EvidenceState::Hold);
    let failed_checks = count_state(checks, EvidenceState::Failed);
    let not_observed_checks = count_state(checks, EvidenceState::NotObserved);
    let covered_checks = total_checks.saturating_sub(not_observed_checks);

    let total_weight: u64 = checks.iter().map(|check| u64::from(check.weight)).sum();
    let verified_weight: u64 = checks
        .iter()
        .filter(|check| check.state == EvidenceState::Verified)
        .map(|check| u64::from(check.weight))
        .sum();

    GeniusStatistics {
        total_checks,
        verified_checks,
        observed_checks,
        hold_checks,
        failed_checks,
        not_observed_checks,
        evidence_coverage_bps: ratio_bps(covered_checks, total_checks),
        verified_alignment_bps: ratio_bps(verified_checks, total_checks),
        weighted_alignment_bps: ratio_bps(verified_weight, total_weight),
        probability_claimed: false,
    }
}

pub fn calculate_release_gates(checks: &[CompatibilityCheck]) -> ReleaseGates {
    ReleaseGates {
        staging_ready: target_ready(checks, GateTarget::Staging),
        publicity_ready: target_ready(checks, GateTarget::Publicity),
        merge_ready: target_ready(checks, GateTarget::Merge),
        production_ready: target_ready(checks, GateTarget::Production),
    }
}

fn target_ready(checks: &[CompatibilityCheck], target: GateTarget) -> bool {
    let required: Vec<&CompatibilityCheck> = checks
        .iter()
        .filter(|check| check.targets.contains(&target))
        .collect();

    !required.is_empty()
        && required
            .iter()
            .all(|check| check.state == EvidenceState::Verified)
}

fn count_state(checks: &[CompatibilityCheck], state: EvidenceState) -> u64 {
    checks.iter().filter(|check| check.state == state).count() as u64
}

fn ratio_bps(numerator: u64, denominator: u64) -> u64 {
    if denominator == 0 {
        return 0;
    }
    numerator.saturating_mul(BASIS_POINTS_SCALE) / denominator
}

#[cfg(test)]
mod tests {
    use super::*;

    fn check(id: &str, state: EvidenceState, targets: Vec<GateTarget>) -> CompatibilityCheck {
        CompatibilityCheck::new(id, state, targets, "test basis")
    }

    #[test]
    fn statistics_are_descriptive_not_probability_claims() {
        let checks = vec![
            check("a", EvidenceState::Verified, vec![GateTarget::Staging]),
            check("b", EvidenceState::Hold, vec![GateTarget::Staging]),
            check("c", EvidenceState::NotObserved, vec![GateTarget::Publicity]),
        ];

        let stats = calculate_statistics(&checks);
        assert_eq!(stats.total_checks, 3);
        assert_eq!(stats.verified_checks, 1);
        assert_eq!(stats.evidence_coverage_bps, 6_666);
        assert_eq!(stats.verified_alignment_bps, 3_333);
        assert!(!stats.probability_claimed);
    }

    #[test]
    fn one_hold_keeps_a_target_closed() {
        let checks = vec![
            check("a", EvidenceState::Verified, vec![GateTarget::Staging]),
            check("b", EvidenceState::Hold, vec![GateTarget::Staging]),
        ];

        assert!(!calculate_release_gates(&checks).staging_ready);
    }

    #[test]
    fn every_target_check_must_be_verified() {
        let checks = vec![
            check("a", EvidenceState::Verified, vec![GateTarget::Staging]),
            check("b", EvidenceState::Verified, vec![GateTarget::Staging]),
        ];

        assert!(calculate_release_gates(&checks).staging_ready);
    }
}
