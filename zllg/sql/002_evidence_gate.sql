PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS entities (
    entity_id       BLOB PRIMARY KEY CHECK(length(entity_id) = 16),
    canonical_name  TEXT,
    entity_type     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    source_id       BLOB PRIMARY KEY CHECK(length(source_id) = 16),
    source_uri      TEXT,
    authority_class TEXT NOT NULL CHECK (
        authority_class IN (
            'AUTHORITATIVE',
            'CONNECTED',
            'USER_SUPPLIED',
            'UNKNOWN'
        )
    ),
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id          BLOB PRIMARY KEY CHECK(length(observation_id) = 16),
    entity_id               BLOB NOT NULL CHECK(length(entity_id) = 16),
    source_id               BLOB NOT NULL CHECK(length(source_id) = 16),
    sequence_no             INTEGER NOT NULL CHECK(sequence_no > 0),
    observed_at             TEXT NOT NULL,
    ingested_at             TEXT NOT NULL,
    artifact_hash           BLOB NOT NULL CHECK(length(artifact_hash) = 32),
    content_hash            BLOB CHECK(content_hash IS NULL OR length(content_hash) = 32),
    previous_observation_id BLOB CHECK(
        previous_observation_id IS NULL OR length(previous_observation_id) = 16
    ),
    evidence_state          TEXT NOT NULL CHECK (
        evidence_state IN ('OBSERVED', 'HOLD', 'REJECTED', 'VERIFIED')
    ),
    provenance_json         TEXT NOT NULL CHECK(json_valid(provenance_json)),
    payload_location        TEXT,

    FOREIGN KEY(entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(previous_observation_id) REFERENCES observations(observation_id),

    UNIQUE(entity_id, sequence_no),
    UNIQUE(entity_id, artifact_hash)
);

CREATE INDEX IF NOT EXISTS idx_observations_entity_ingested
    ON observations(entity_id, ingested_at);

CREATE INDEX IF NOT EXISTS idx_observations_source
    ON observations(source_id);

CREATE TABLE IF NOT EXISTS evidence_claims (
    claim_id           BLOB PRIMARY KEY CHECK(length(claim_id) = 16),
    observation_id     BLOB NOT NULL CHECK(length(observation_id) = 16),
    claim_text         TEXT NOT NULL,
    claim_class        TEXT NOT NULL CHECK (
        claim_class IN ('OBSERVED', 'CORRELATED', 'CAUSAL', 'UNVERIFIED')
    ),
    verification_state TEXT NOT NULL CHECK (
        verification_state IN (
            'PENDING',
            'SUPPORTED',
            'CONTRADICTED',
            'INSUFFICIENT'
        )
    ),

    FOREIGN KEY(observation_id) REFERENCES observations(observation_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_observation
    ON evidence_claims(observation_id);

CREATE TABLE IF NOT EXISTS lineage (
    resulting_state_hash BLOB PRIMARY KEY CHECK(length(resulting_state_hash) = 32),
    observation_id       BLOB NOT NULL UNIQUE CHECK(length(observation_id) = 16),

    FOREIGN KEY(observation_id) REFERENCES observations(observation_id)
);

CREATE TABLE IF NOT EXISTS repair_center (
    entity_id      BLOB NOT NULL CHECK(length(entity_id) = 16),
    candidate_hash BLOB NOT NULL CHECK(length(candidate_hash) = 32),
    reason_code    TEXT NOT NULL,
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL,

    PRIMARY KEY(entity_id, candidate_hash),
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);

-- I02: observations are append-only. Corrections are represented as new observations.
CREATE TRIGGER IF NOT EXISTS observations_no_update
BEFORE UPDATE ON observations
BEGIN
    SELECT RAISE(ABORT, 'observations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS observations_no_delete
BEFORE DELETE ON observations
BEGIN
    SELECT RAISE(ABORT, 'observations are append-only');
END;

-- A parent observation, when present, must belong to the same entity.
CREATE TRIGGER IF NOT EXISTS observations_parent_same_entity
BEFORE INSERT ON observations
WHEN NEW.previous_observation_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM observations p
            WHERE p.observation_id = NEW.previous_observation_id
              AND p.entity_id = NEW.entity_id
        )
        THEN RAISE(ABORT, 'previous observation belongs to a different entity')
    END;
END;
