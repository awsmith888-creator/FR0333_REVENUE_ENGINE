use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntityClass {
    Raven,
    Steward,
    Colonel,
    Sophie,
}

impl EntityClass {
    fn prefix(self) -> &'static str {
        match self {
            Self::Raven => "RAVEN",
            Self::Steward => "STW",
            Self::Colonel => "COL",
            Self::Sophie => "SOPHIE",
        }
    }

    fn expected_parent(self) -> Option<EntityClass> {
        match self {
            Self::Raven => None,
            Self::Steward => Some(Self::Raven),
            Self::Colonel => Some(Self::Steward),
            Self::Sophie => Some(Self::Colonel),
        }
    }

    fn as_str(self) -> &'static str {
        self.prefix()
    }
}

#[derive(Debug, Clone)]
pub struct MajorIndexRecord<'a> {
    pub reference_id: &'a str,
    pub entity_class: EntityClass,
    pub created_at: &'a str,
    pub parent_reference_id: Option<&'a str>,
    pub evidence_state: &'a str,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InsertOutcome {
    Inserted,
    Hold { reason: &'static str },
}

#[derive(Debug, Error)]
pub enum MajorIndexError {
    #[error(transparent)]
    Sqlite(#[from] rusqlite::Error),
}

pub fn initialize_major_index_schema(conn: &Connection) -> Result<(), MajorIndexError> {
    conn.execute_batch(
        "PRAGMA foreign_keys = ON;
         CREATE TABLE IF NOT EXISTS major_index (
             reference_id TEXT PRIMARY KEY,
             entity_class TEXT NOT NULL,
             created_at TEXT NOT NULL,
             parent_reference_id TEXT,
             evidence_state TEXT NOT NULL,
             FOREIGN KEY(parent_reference_id) REFERENCES major_index(reference_id)
         );
         CREATE TABLE IF NOT EXISTS unresolved_identity (
             reference_id TEXT NOT NULL,
             entity_class TEXT NOT NULL,
             parent_reference_id TEXT,
             evidence_state TEXT NOT NULL,
             reason_code TEXT NOT NULL,
             created_at TEXT NOT NULL
         );",
    )?;
    Ok(())
}

pub fn insert_record(
    conn: &mut Connection,
    record: &MajorIndexRecord<'_>,
) -> Result<InsertOutcome, MajorIndexError> {
    if !reference_syntax_valid(record.reference_id, record.entity_class) {
        return hold(conn, record, "MALFORMED_REFERENCE");
    }

    if !required_fields_valid(record) {
        return hold(conn, record, "MISSING_REQUIRED_FIELD");
    }

    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;

    let duplicate: Option<i64> = tx
        .query_row(
            "SELECT 1 FROM major_index WHERE reference_id = ?1",
            params![record.reference_id],
            |row| row.get(0),
        )
        .optional()?;

    if duplicate.is_some() {
        tx.rollback()?;
        return hold(conn, record, "DUPLICATE_REFERENCE");
    }

    match record.entity_class.expected_parent() {
        None => {
            if record.parent_reference_id.is_some() {
                tx.rollback()?;
                return hold(conn, record, "RAVEN_MUST_NOT_HAVE_PARENT");
            }
        }
        Some(expected_parent) => {
            let Some(parent_id) = record.parent_reference_id else {
                tx.rollback()?;
                return hold(conn, record, "MISSING_PARENT");
            };

            let parent_class: Option<String> = tx
                .query_row(
                    "SELECT entity_class FROM major_index WHERE reference_id = ?1",
                    params![parent_id],
                    |row| row.get(0),
                )
                .optional()?;

            let Some(parent_class) = parent_class else {
                tx.rollback()?;
                return hold(conn, record, "PARENT_NOT_FOUND");
            };

            if parent_class != expected_parent.as_str() {
                tx.rollback()?;
                return hold(conn, record, "PARENT_CLASS_MISMATCH");
            }
        }
    }

    tx.execute(
        "INSERT INTO major_index (
            reference_id,
            entity_class,
            created_at,
            parent_reference_id,
            evidence_state
         ) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![
            record.reference_id,
            record.entity_class.as_str(),
            record.created_at,
            record.parent_reference_id,
            record.evidence_state,
        ],
    )?;
    tx.commit()?;

    Ok(InsertOutcome::Inserted)
}

pub fn update_role_metadata_without_reference_change(
    conn: &Connection,
    reference_id: &str,
    new_evidence_state: &str,
) -> Result<bool, MajorIndexError> {
    let changed = conn.execute(
        "UPDATE major_index SET evidence_state = ?2 WHERE reference_id = ?1",
        params![reference_id, new_evidence_state],
    )?;
    Ok(changed == 1)
}

fn reference_syntax_valid(reference_id: &str, class: EntityClass) -> bool {
    let expected_prefix = format!("FR0333-{}-", class.prefix());
    let Some(sequence) = reference_id.strip_prefix(&expected_prefix) else {
        return false;
    };
    sequence.len() == 6 && sequence.chars().all(|ch| ch.is_ascii_digit())
}

fn required_fields_valid(record: &MajorIndexRecord<'_>) -> bool {
    !record.reference_id.is_empty()
        && !record.created_at.is_empty()
        && !record.evidence_state.is_empty()
}

fn hold(
    conn: &Connection,
    record: &MajorIndexRecord<'_>,
    reason: &'static str,
) -> Result<InsertOutcome, MajorIndexError> {
    conn.execute(
        "INSERT INTO unresolved_identity (
            reference_id,
            entity_class,
            parent_reference_id,
            evidence_state,
            reason_code,
            created_at
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![
            record.reference_id,
            record.entity_class.as_str(),
            record.parent_reference_id,
            record.evidence_state,
            reason,
            record.created_at,
        ],
    )?;
    Ok(InsertOutcome::Hold { reason })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn connection() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        initialize_major_index_schema(&conn).unwrap();
        conn
    }

    fn record<'a>(
        reference_id: &'a str,
        entity_class: EntityClass,
        parent_reference_id: Option<&'a str>,
    ) -> MajorIndexRecord<'a> {
        MajorIndexRecord {
            reference_id,
            entity_class,
            created_at: "2026-08-13T04:34:00-04:00",
            parent_reference_id,
            evidence_state: "VERIFIED",
        }
    }

    #[test]
    fn valid_raven_to_steward_to_colonel_to_sophie_chain_inserts() {
        let mut conn = connection();

        assert_eq!(
            insert_record(
                &mut conn,
                &record("FR0333-RAVEN-000001", EntityClass::Raven, None)
            )
            .unwrap(),
            InsertOutcome::Inserted
        );
        assert_eq!(
            insert_record(
                &mut conn,
                &record(
                    "FR0333-STW-000001",
                    EntityClass::Steward,
                    Some("FR0333-RAVEN-000001")
                )
            )
            .unwrap(),
            InsertOutcome::Inserted
        );
        assert_eq!(
            insert_record(
                &mut conn,
                &record(
                    "FR0333-COL-000001",
                    EntityClass::Colonel,
                    Some("FR0333-STW-000001")
                )
            )
            .unwrap(),
            InsertOutcome::Inserted
        );
        assert_eq!(
            insert_record(
                &mut conn,
                &record(
                    "FR0333-SOPHIE-000001",
                    EntityClass::Sophie,
                    Some("FR0333-COL-000001")
                )
            )
            .unwrap(),
            InsertOutcome::Inserted
        );
    }

    #[test]
    fn duplicate_reference_is_held_not_globally_frozen() {
        let mut conn = connection();
        let raven = record("FR0333-RAVEN-000001", EntityClass::Raven, None);
        insert_record(&mut conn, &raven).unwrap();

        let duplicate = insert_record(&mut conn, &raven).unwrap();
        assert_eq!(
            duplicate,
            InsertOutcome::Hold {
                reason: "DUPLICATE_REFERENCE"
            }
        );

        let count: i64 = conn
            .query_row("SELECT COUNT(*) FROM major_index", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn malformed_reference_is_held() {
        let mut conn = connection();
        let outcome = insert_record(
            &mut conn,
            &record("FR0333-SOPHIE-1", EntityClass::Sophie, Some("missing")),
        )
        .unwrap();

        assert_eq!(
            outcome,
            InsertOutcome::Hold {
                reason: "MALFORMED_REFERENCE"
            }
        );
    }

    #[test]
    fn missing_parent_is_held() {
        let mut conn = connection();
        let outcome = insert_record(
            &mut conn,
            &record("FR0333-STW-000001", EntityClass::Steward, None),
        )
        .unwrap();
        assert_eq!(
            outcome,
            InsertOutcome::Hold {
                reason: "MISSING_PARENT"
            }
        );
    }

    #[test]
    fn wrong_parent_class_is_held() {
        let mut conn = connection();
        insert_record(
            &mut conn,
            &record("FR0333-RAVEN-000001", EntityClass::Raven, None),
        )
        .unwrap();

        let outcome = insert_record(
            &mut conn,
            &record(
                "FR0333-SOPHIE-000001",
                EntityClass::Sophie,
                Some("FR0333-RAVEN-000001"),
            ),
        )
        .unwrap();
        assert_eq!(
            outcome,
            InsertOutcome::Hold {
                reason: "PARENT_CLASS_MISMATCH"
            }
        );
    }

    #[test]
    fn role_metadata_update_preserves_reference_id() {
        let mut conn = connection();
        insert_record(
            &mut conn,
            &record("FR0333-RAVEN-000001", EntityClass::Raven, None),
        )
        .unwrap();

        assert!(
            update_role_metadata_without_reference_change(
                &conn,
                "FR0333-RAVEN-000001",
                "OBSERVED"
            )
            .unwrap()
        );

        let reference: String = conn
            .query_row(
                "SELECT reference_id FROM major_index WHERE reference_id = 'FR0333-RAVEN-000001'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(reference, "FR0333-RAVEN-000001");
    }
}
