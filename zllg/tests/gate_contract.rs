use std::path::PathBuf;
use zllg::gate::{EvidenceBlock, GateError, GateState, ZeroLocalLogGate};

fn setup_clean_sandbox() -> (ZeroLocalLogGate, PathBuf) {
    let sandbox = PathBuf::from("/tmp/fr0333_sandbox");
    (ZeroLocalLogGate::new(&sandbox), sandbox)
}

#[test]
fn zero_evidence_yields_hold() {
    let (mut gate, _) = setup_clean_sandbox();
    assert_eq!(gate.state(), GateState::Unknown);
    assert_eq!(gate.evaluate_gate(None).unwrap(), GateState::Hold);
}

#[test]
fn structurally_valid_runtime_evidence_yields_verified() {
    let (mut gate, sandbox) = setup_clean_sandbox();
    let evidence = EvidenceBlock {
        provenance_source: sandbox.join("build_manifest.json"),
        payload_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".into(),
        is_simulation: false,
    };

    assert_eq!(
        gate.evaluate_gate(Some(evidence)).unwrap(),
        GateState::Verified
    );
}

#[test]
fn simulation_cannot_impersonate_runtime() {
    let (mut gate, sandbox) = setup_clean_sandbox();
    let evidence = EvidenceBlock {
        provenance_source: sandbox.join("mock_artifact.json"),
        payload_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".into(),
        is_simulation: true,
    };

    assert!(matches!(
        gate.evaluate_gate(Some(evidence)),
        Err(GateError::SimulationImpersonation)
    ));
    assert_eq!(gate.state(), GateState::Hold);
}

#[test]
fn malformed_digest_cannot_promote() {
    let (mut gate, sandbox) = setup_clean_sandbox();
    let evidence = EvidenceBlock {
        provenance_source: sandbox.join("bad_manifest.json"),
        payload_hash: "not-a-sha256".into(),
        is_simulation: false,
    };

    assert_eq!(gate.evaluate_gate(Some(evidence)).unwrap(), GateState::Hold);
}

#[test]
fn provenance_outside_sandbox_is_rejected() {
    let (mut gate, _) = setup_clean_sandbox();
    let evidence = EvidenceBlock {
        provenance_source: PathBuf::from("/etc/passwd"),
        payload_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".into(),
        is_simulation: false,
    };

    assert!(matches!(
        gate.evaluate_gate(Some(evidence)),
        Err(GateError::PathViolation(_))
    ));
    assert_eq!(gate.state(), GateState::Hold);
}
