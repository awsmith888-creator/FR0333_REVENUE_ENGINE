use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use sha2::{Digest, Sha256};
use thiserror::Error;

pub const EVIDENCE_GATE_SCHEMA: &str = include_str!("../sql/002_evidence_gate.sql");

pub type ObservationId = [u8; 16];
pub type SourceId = [u8; 16];
pub type ArtifactHash = [u8; 32];

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AppendOutcome {
    Appended {
        observation_id: ObservationId,
        sequence_no: i64,
        artifact_hash: ArtifactHash,
    },
    Duplicate {
        observation_id: ObservationId,
        artifact_hash: ArtifactHash,
    },
}

#[derive(Debug)]
pub struct ObservationInput<'a> {
    pub observation_id: ObservationId,
    pub entity_id: [u8; 16],
    pub source_id: SourceId,
    pub observed_at: &'a str,
    pub ingested_at: &'a str,
    pub payload: &'a [u8],
    pub content_hash: Option<ArtifactHash>,
    pub provenance_json: &'a str,
    pub payload_location: Option<&'a str>,
}

#[derive(Debug, Error)]
pub enum EvidenceGateError {
    #[error(transparent)]
    Sqlite(#[from] rusqlite::Error),

    #[error("stored observation id has invalid length: {0}")]
    InvalidObservationIdLength(usize),
}

pub fn initialize_schema(conn: &Connection) -> Result<(), EvidenceGateError> {
    conn.execute_batch(EVIDENCE_GATE_SCHEMA)?;
    Ok(())
}

pub fn hash_exact_bytes(payload: &[u8]) -> ArtifactHash {
    Sha256::digest(payload).into()
}

pub fn append_observation(
    conn: &mut Connection,
    input: &ObservationInput<'_>,
) -> Result<AppendOutcome, EvidenceGateError> {
    let artifact_hash = hash_exact_bytes(input.payload);
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;

    let duplicate: Option<Vec<u8>> = tx
        .query_row(
            "SELECT observation_id
             FROM observations
             WHERE entity_id = ?1 AND artifact_hash = ?2",
            params![input.entity_id.as_slice(), artifact_hash.as_slice()],
            |row| row.get(0),
        )
        .optional()?;

    if let Some(existing) = duplicate {
        let observation_id = decode_observation_id(existing)?;
        tx.commit()?;
        return Ok(AppendOutcome::Duplicate {
            observation_id,
            artifact_hash,
        });
    }

    let previous: Option<(Vec<u8>, i64)> = tx
        .query_row(
            "SELECT observation_id, sequence_no
             FROM observations
             WHERE entity_id = ?1
             ORDER BY sequence_no DESC
             LIMIT 1",
            params![input.entity_id.as_slice()],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .optional()?;

    let (previous_observation_id, sequence_no) = match previous {
        Some((id, sequence_no)) => (Some(decode_observation_id(id)?), sequence_no + 1),
        None => (None, 1),
    };

    tx.execute(
        "INSERT INTO observations (
            observation_id,
            entity_id,
            source_id,
            sequence_no,
            observed_at,
            ingested_at,
            artifact_hash,
            content_hash,
            previous_observation_id,
            evidence_state,
            provenance_json,
            payload_location
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 'OBSERVED', ?10, ?11)",
        params![
            input.observation_id.as_slice(),
            input.entity_id.as_slice(),
            input.source_id.as_slice(),
            sequence_no,
            input.observed_at,
            input.ingested_at,
            artifact_hash.as_slice(),
            input.content_hash.as_ref().map(|hash| hash.as_slice()),
            previous_observation_id.as_ref().map(|id| id.as_slice()),
            input.provenance_json,
            input.payload_location,
        ],
    )?;

    tx.commit()?;

    Ok(AppendOutcome::Appended {
        observation_id: input.observation_id,
        sequence_no,
        artifact_hash,
    })
}

fn decode_observation_id(bytes: Vec<u8>) -> Result<ObservationId, EvidenceGateError> {
    let len = bytes.len();
    bytes
        .try_into()
        .map_err(|_| EvidenceGateError::InvalidObservationIdLength(len))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seeded_connection() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        initialize_schema(&conn).unwrap();

        conn.execute(
            "INSERT INTO entities (entity_id, canonical_name, entity_type, created_at)
             VALUES (?1, 'E01', 'TEST', '2026-08-12T00:00:00Z')",
            params![[1u8; 16].as_slice()],
        )
        .unwrap();

        conn.execute(
            "INSERT INTO sources (source_id, source_uri, authority_class, created_at)
             VALUES (?1, 'memory://test', 'USER_SUPPLIED', '2026-08-12T00:00:00Z')",
            params![[2u8; 16].as_slice()],
        )
        .unwrap();

        conn
    }

    fn input<'a>(observation_id: ObservationId, payload: &'a [u8]) -> ObservationInput<'a> {
        ObservationInput {
            observation_id,
            entity_id: [1u8; 16],
            source_id: [2u8; 16],
            observed_at: "2026-08-12T00:00:00Z",
            ingested_at: "2026-08-12T00:00:01Z",
            payload,
            content_hash: None,
            provenance_json: r#"{"source":"test"}"#,
            payload_location: None,
        }
    }

    #[test]
    fn same_bytes_collapse_to_existing_observation() {
        let mut conn = seeded_connection();

        let first = append_observation(&mut conn, &input([3u8; 16], b"same bytes")).unwrap();
        let second = append_observation(&mut conn, &input([4u8; 16], b"same bytes")).unwrap();

        assert!(matches!(
            first,
            AppendOutcome::Appended { sequence_no: 1, .. }
        ));
        assert!(matches!(
            second,
            AppendOutcome::Duplicate { observation_id, .. } if observation_id == [3u8; 16]
        ));
    }

    #[test]
    fn changed_bytes_append_and_link_to_previous_observation() {
        let mut conn = seeded_connection();

        append_observation(&mut conn, &input([3u8; 16], b"AAA")).unwrap();
        let second = append_observation(&mut conn, &input([4u8; 16], b"BBB")).unwrap();

        assert!(matches!(
            second,
            AppendOutcome::Appended { sequence_no: 2, .. }
        ));

        let parent: Vec<u8> = conn
            .query_row(
                "SELECT previous_observation_id FROM observations WHERE observation_id = ?1",
                params![[4u8; 16].as_slice()],
                |row| row.get(0),
            )
            .unwrap();

        assert_eq!(parent, [3u8; 16]);
    }

    #[test]
    fn observation_rows_cannot_be_updated_or_deleted() {
        let mut conn = seeded_connection();
        append_observation(&mut conn, &input([3u8; 16], b"immutable")).unwrap();

        let update = conn.execute(
            "UPDATE observations SET evidence_state = 'VERIFIED' WHERE observation_id = ?1",
            params![[3u8; 16].as_slice()],
        );
        let delete = conn.execute(
            "DELETE FROM observations WHERE observation_id = ?1",
            params![[3u8; 16].as_slice()],
        );

        assert!(update.is_err());
        assert!(delete.is_err());
    }
}
