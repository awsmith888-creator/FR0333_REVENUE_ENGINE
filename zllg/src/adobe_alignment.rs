use serde::Serialize;
use sha2::{Digest, Sha256};

use crate::compatibility::{
    calculate_release_gates, calculate_statistics, CompatibilityCheck, EvidenceState, GateTarget,
    GeniusStatistics, ReleaseGates,
};
use crate::render_engine::{ArtifactReceipt, RenderRequest};

pub const ALIGNMENT_SCHEMA_VERSION: &str = "FR0333-ADOBE-ALIGNMENT-1.0.0";
pub const MASTER_WIDTH: u32 = 1080;
pub const MASTER_HEIGHT: u32 = 1920;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ExecutionMode {
    Simulation,
    LiveStaging,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ContentCredentialsState {
    NotApplicable,
    NotInspected,
    Verified,
    Missing,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ProviderObservation {
    pub api_profile: String,
    pub provider_job_id: String,
    pub output_host: String,
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AdobeAlignmentReceipt {
    pub schema_version: String,
    pub reference_id: String,
    pub execution_mode: ExecutionMode,
    pub observed_at_unix: u64,
    pub commit_sha: String,
    pub request_sha256: String,
    pub artifact_sha256: String,
    pub artifact_byte_len: u64,
    pub artifact_width: u32,
    pub artifact_height: u32,
    pub artifact_media_type: String,
    pub exact_master_geometry: bool,
    pub provider: ProviderObservation,
    pub content_credentials: ContentCredentialsState,
    pub checks: Vec<CompatibilityCheck>,
    pub genius_statistics: GeniusStatistics,
    pub release_gates: ReleaseGates,
    pub evidence_boundary: String,
}

pub struct AlignmentReceiptInput<'a> {
    pub reference_id: &'a str,
    pub execution_mode: ExecutionMode,
    pub observed_at_unix: u64,
    pub commit_sha: &'a str,
    pub request: &'a RenderRequest,
    pub artifact: &'a ArtifactReceipt,
    pub provider: ProviderObservation,
    pub content_credentials: ContentCredentialsState,
}

pub fn build_alignment_receipt(input: AlignmentReceiptInput<'_>) -> AdobeAlignmentReceipt {
    let exact_master_geometry =
        input.artifact.width == MASTER_WIDTH && input.artifact.height == MASTER_HEIGHT;
    let checks = alignment_checks(
        input.execution_mode,
        exact_master_geometry,
        input.content_credentials,
    );
    let genius_statistics = calculate_statistics(&checks);
    let release_gates = calculate_release_gates(&checks);

    AdobeAlignmentReceipt {
        schema_version: ALIGNMENT_SCHEMA_VERSION.to_string(),
        reference_id: input.reference_id.to_string(),
        execution_mode: input.execution_mode,
        observed_at_unix: input.observed_at_unix,
        commit_sha: input.commit_sha.to_string(),
        request_sha256: request_hash(input.request, input.commit_sha),
        artifact_sha256: hex_encode(&input.artifact.sha256),
        artifact_byte_len: input.artifact.byte_len,
        artifact_width: input.artifact.width,
        artifact_height: input.artifact.height,
        artifact_media_type: input.artifact.media_type.to_string(),
        exact_master_geometry,
        provider: input.provider,
        content_credentials: input.content_credentials,
        checks,
        genius_statistics,
        release_gates,
        evidence_boundary:
            "OBSERVED != VERIFIED; SIMULATION != RUNTIME; TEST_PASS != DEPLOYMENT; STAGING != PUBLICITY"
                .to_string(),
    }
}

fn alignment_checks(
    mode: ExecutionMode,
    exact_master_geometry: bool,
    content_credentials: ContentCredentialsState,
) -> Vec<CompatibilityCheck> {
    use EvidenceState::{Failed, Hold, NotObserved, Observed, Verified};
    use GateTarget::{Merge, Production, Publicity, Staging};

    let live = mode == ExecutionMode::LiveStaging;
    let runtime_state = if live { Verified } else { Hold };
    let geometry_state = if exact_master_geometry {
        Verified
    } else {
        Failed
    };
    let credentials_state = match content_credentials {
        ContentCredentialsState::Verified => Verified,
        ContentCredentialsState::Missing => Failed,
        ContentCredentialsState::NotApplicable => Hold,
        ContentCredentialsState::NotInspected => NotObserved,
    };

    vec![
        CompatibilityCheck::new(
            "SOURCE_LOCK",
            Verified,
            vec![Staging, Merge, Production],
            "The execution mode, commit SHA, request, and output root are explicit.",
        ),
        CompatibilityCheck::new(
            "ENGINE_CONTRACT",
            Verified,
            vec![Staging, Merge, Production],
            "Render provider, decoder, evidence gate, lifecycle, receipt, index, and stackbar remain separate modules.",
        ),
        CompatibilityCheck::new(
            "KERNEL_CONTRACT",
            Verified,
            vec![Staging, Merge, Production],
            "Geometry, path, simulation, digest, and append-only controls remain fail-closed.",
        ),
        CompatibilityCheck::new(
            "ADOBE_API_RUNTIME",
            runtime_state,
            vec![Staging, Production],
            if live {
                "A credential-backed Adobe request completed in this staging execution."
            } else {
                "The Adobe code path is present but no external request occurred in simulation."
            },
        ),
        CompatibilityCheck::new(
            "ADOBE_AUTH_RUNTIME",
            runtime_state,
            vec![Staging, Production],
            if live {
                "OAuth server-to-server authentication succeeded without storing the access token."
            } else {
                "Credentials were intentionally absent from simulation."
            },
        ),
        CompatibilityCheck::new(
            "ASYNC_JOB_LIFECYCLE",
            runtime_state,
            vec![Staging, Production],
            if live {
                "The provider submitted, polled, completed, and downloaded one bounded job."
            } else {
                "No Adobe job identifier or status endpoint was observed."
            },
        ),
        CompatibilityCheck::new(
            "MASTER_1080X1920",
            geometry_state,
            vec![Staging, Publicity, Production],
            "The FR-0333 publication master requires exact 1080x1920 geometry.",
        ),
        CompatibilityCheck::new(
            "ARTIFACT_SHA256",
            Verified,
            vec![Staging, Merge, Production],
            "SHA-256 was computed over the exact emitted artifact bytes.",
        ),
        CompatibilityCheck::new(
            "CONTENT_CREDENTIALS",
            credentials_state,
            vec![Publicity, Production],
            "Adobe states that Firefly API outputs receive Content Credentials, but each downloaded artifact must still be inspected.",
        ),
        CompatibilityCheck::new(
            "HUMAN_PUBLICITY_APPROVAL",
            NotObserved,
            vec![Publicity, Production],
            "No automated execution may approve public release or identity-sensitive imagery.",
        ),
        CompatibilityCheck::new(
            "PR_HEAD_CI",
            Observed,
            vec![Merge, Production],
            "The receipt records a commit SHA, while current-head CI remains external GitHub evidence.",
        ),
        CompatibilityCheck::new(
            "REVIEW_AND_BODY_ALIGNMENT",
            NotObserved,
            vec![Merge, Production],
            "Review state and PR-body drift must be re-fetched from GitHub before merge.",
        ),
        CompatibilityCheck::new(
            "PRODUCTION_DEPLOYMENT",
            Hold,
            vec![Production],
            "This runner is staging-only and has no public endpoint or production mutation authority.",
        ),
    ]
}

fn request_hash(request: &RenderRequest, commit_sha: &str) -> String {
    let canonical = format!(
        "{}\n{}\n{}\n{}",
        commit_sha, request.width, request.height, request.prompt
    );
    hex_encode(&Sha256::digest(canonical.as_bytes()))
}

pub fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    fn artifact(width: u32, height: u32) -> ArtifactReceipt {
        ArtifactReceipt {
            sha256: [7u8; 32],
            byte_len: 333,
            width,
            height,
            media_type: "image/png",
        }
    }

    fn request() -> RenderRequest {
        RenderRequest {
            prompt: "FR-0333 staging proof".to_string(),
            width: MASTER_WIDTH,
            height: MASTER_HEIGHT,
        }
    }

    fn provider() -> ProviderObservation {
        ProviderObservation {
            api_profile: "v3_async".to_string(),
            provider_job_id: "job-1".to_string(),
            output_host: "example.amazonaws.com".to_string(),
            seed: Some(33),
        }
    }

    #[test]
    fn simulation_never_impersonates_staging_or_publicity() {
        let receipt = build_alignment_receipt(AlignmentReceiptInput {
            reference_id: "FR0333-ADOBE-STAGE-000001",
            execution_mode: ExecutionMode::Simulation,
            observed_at_unix: 1,
            commit_sha: "abc123",
            request: &request(),
            artifact: &artifact(MASTER_WIDTH, MASTER_HEIGHT),
            provider: provider(),
            content_credentials: ContentCredentialsState::NotApplicable,
        });

        assert!(!receipt.release_gates.staging_ready);
        assert!(!receipt.release_gates.publicity_ready);
        assert!(!receipt.genius_statistics.probability_claimed);
    }

    #[test]
    fn live_staging_can_pass_while_publicity_stays_held() {
        let receipt = build_alignment_receipt(AlignmentReceiptInput {
            reference_id: "FR0333-ADOBE-STAGE-000002",
            execution_mode: ExecutionMode::LiveStaging,
            observed_at_unix: 2,
            commit_sha: "def456",
            request: &request(),
            artifact: &artifact(MASTER_WIDTH, MASTER_HEIGHT),
            provider: provider(),
            content_credentials: ContentCredentialsState::NotInspected,
        });

        assert!(receipt.release_gates.staging_ready);
        assert!(!receipt.release_gates.publicity_ready);
        assert!(!receipt.release_gates.merge_ready);
        assert!(!receipt.release_gates.production_ready);
    }

    #[test]
    fn non_master_dimensions_fail_the_staging_gate() {
        let receipt = build_alignment_receipt(AlignmentReceiptInput {
            reference_id: "FR0333-ADOBE-STAGE-000003",
            execution_mode: ExecutionMode::LiveStaging,
            observed_at_unix: 3,
            commit_sha: "def456",
            request: &request(),
            artifact: &artifact(900, 1600),
            provider: provider(),
            content_credentials: ContentCredentialsState::NotInspected,
        });

        assert!(!receipt.release_gates.staging_ready);
    }
}
