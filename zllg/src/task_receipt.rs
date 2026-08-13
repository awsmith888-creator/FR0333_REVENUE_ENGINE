use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::task_lifecycle::TaskState;

pub type StateHash = [u8; 32];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskReceipt {
    pub task_id: String,
    pub reference_id: String,
    pub commit_sha: String,
    pub schema_version: String,
    pub previous_state_hash: StateHash,
    pub resulting_state_hash: StateHash,
    pub started_at: String,
    pub completed_at: String,
    pub task_state: TaskState,
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum TaskReceiptError {
    #[error("task receipt requires committed transaction")]
    TransactionNotCommitted,
    #[error("task receipt requires executed task state")]
    TaskNotExecuted,
    #[error("receipt metadata field is empty: {0}")]
    EmptyField(&'static str),
}

pub struct ReceiptInput<'a> {
    pub task_id: &'a str,
    pub reference_id: &'a str,
    pub commit_sha: &'a str,
    pub schema_version: &'a str,
    pub previous_state_hash: StateHash,
    pub canonical_state_bytes: &'a [u8],
    pub started_at: &'a str,
    pub completed_at: &'a str,
    pub committed: bool,
    pub task_state: TaskState,
}

pub fn hash_canonical_state(bytes: &[u8]) -> StateHash {
    Sha256::digest(bytes).into()
}

pub fn build_receipt(input: ReceiptInput<'_>) -> Result<TaskReceipt, TaskReceiptError> {
    if !input.committed {
        return Err(TaskReceiptError::TransactionNotCommitted);
    }
    if input.task_state != TaskState::Executed {
        return Err(TaskReceiptError::TaskNotExecuted);
    }

    for (name, value) in [
        ("task_id", input.task_id),
        ("reference_id", input.reference_id),
        ("commit_sha", input.commit_sha),
        ("schema_version", input.schema_version),
        ("started_at", input.started_at),
        ("completed_at", input.completed_at),
    ] {
        if value.is_empty() {
            return Err(TaskReceiptError::EmptyField(name));
        }
    }

    Ok(TaskReceipt {
        task_id: input.task_id.to_string(),
        reference_id: input.reference_id.to_string(),
        commit_sha: input.commit_sha.to_string(),
        schema_version: input.schema_version.to_string(),
        previous_state_hash: input.previous_state_hash,
        resulting_state_hash: hash_canonical_state(input.canonical_state_bytes),
        started_at: input.started_at.to_string(),
        completed_at: input.completed_at.to_string(),
        task_state: TaskState::Receipted,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn input<'a>(bytes: &'a [u8]) -> ReceiptInput<'a> {
        ReceiptInput {
            task_id: "TASK-000001",
            reference_id: "FR0333-SOPHIE-000001",
            commit_sha: "abc123",
            schema_version: "1.0.0",
            previous_state_hash: [0u8; 32],
            canonical_state_bytes: bytes,
            started_at: "2026-08-13T16:00:00-04:00",
            completed_at: "2026-08-13T16:00:01-04:00",
            committed: true,
            task_state: TaskState::Executed,
        }
    }

    #[test]
    fn committed_execution_produces_receipt_hash() {
        let receipt = build_receipt(input(b"canonical state")).unwrap();
        assert_eq!(receipt.task_state, TaskState::Receipted);
        assert_eq!(receipt.resulting_state_hash, hash_canonical_state(b"canonical state"));
    }

    #[test]
    fn uncommitted_transaction_cannot_be_receipted() {
        let mut candidate = input(b"state");
        candidate.committed = false;
        assert_eq!(
            build_receipt(candidate),
            Err(TaskReceiptError::TransactionNotCommitted)
        );
    }

    #[test]
    fn state_change_changes_receipt_hash() {
        let first = build_receipt(input(b"state-a")).unwrap();
        let second = build_receipt(input(b"state-b")).unwrap();
        assert_ne!(first.resulting_state_hash, second.resulting_state_hash);
    }
}
