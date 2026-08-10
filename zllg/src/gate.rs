use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum GateError {
    #[error("simulation artifact cannot be promoted as runtime evidence")]
    SimulationImpersonation,
    #[error("provenance path is outside the sandbox: {0}")]
    PathViolation(PathBuf),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GateState {
    Unknown,
    Hold,
    Verified,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceBlock {
    pub provenance_source: PathBuf,
    pub payload_hash: String,
    pub is_simulation: bool,
}

pub struct ZeroLocalLogGate {
    sandbox_root: PathBuf,
    state: GateState,
}

impl ZeroLocalLogGate {
    pub fn new<P: AsRef<Path>>(root: P) -> Self {
        Self {
            sandbox_root: root.as_ref().to_path_buf(),
            state: GateState::Unknown,
        }
    }

    pub fn state(&self) -> GateState {
        self.state
    }

    pub fn evaluate_gate(
        &mut self,
        evidence: Option<EvidenceBlock>,
    ) -> Result<GateState, GateError> {
        let Some(block) = evidence else {
            self.state = GateState::Hold;
            return Ok(self.state);
        };

        if !block.provenance_source.starts_with(&self.sandbox_root) {
            self.state = GateState::Hold;
            return Err(GateError::PathViolation(block.provenance_source));
        }

        if block.is_simulation {
            self.state = GateState::Hold;
            return Err(GateError::SimulationImpersonation);
        }

        // Prototype integrity rule only. A later implementation must parse and
        // cryptographically verify the digest rather than trusting string length.
        if block.payload_hash.len() != 64
            || !block.payload_hash.chars().all(|c| c.is_ascii_hexdigit())
        {
            self.state = GateState::Hold;
            return Ok(self.state);
        }

        self.state = GateState::Verified;
        Ok(self.state)
    }
}
