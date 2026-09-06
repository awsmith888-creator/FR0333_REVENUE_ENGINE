use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum GateError {
    #[error("simulation artifact cannot be promoted as runtime evidence")]
    SimulationImpersonation,
    #[error("provenance path is outside the sandbox: {0}")]
    PathViolation(PathBuf),
    #[error("declared payload hash does not match the exact payload bytes")]
    PayloadHashMismatch,
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
    pub payload: Vec<u8>,
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

        let Some(declared_hash) = decode_sha256(&block.payload_hash) else {
            self.state = GateState::Hold;
            return Ok(self.state);
        };
        let computed_hash: [u8; 32] = Sha256::digest(&block.payload).into();
        if declared_hash != computed_hash {
            self.state = GateState::Hold;
            return Err(GateError::PayloadHashMismatch);
        }

        self.state = GateState::Verified;
        Ok(self.state)
    }
}

fn decode_sha256(value: &str) -> Option<[u8; 32]> {
    if value.len() != 64 {
        return None;
    }

    let mut decoded = [0u8; 32];
    for (index, pair) in value.as_bytes().as_chunks::<2>().0.iter().enumerate() {
        let high = hex_value(pair[0])?;
        let low = hex_value(pair[1])?;
        decoded[index] = (high << 4) | low;
    }
    Some(decoded)
}

fn hex_value(value: u8) -> Option<u8> {
    match value {
        b'0'..=b'9' => Some(value - b'0'),
        b'a'..=b'f' => Some(value - b'a' + 10),
        b'A'..=b'F' => Some(value - b'A' + 10),
        _ => None,
    }
}
