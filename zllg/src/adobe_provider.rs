use std::collections::HashMap;
use std::env;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use reqwest::blocking::{Client, Response};
use reqwest::header::RETRY_AFTER;
use reqwest::redirect::Policy;
use reqwest::{StatusCode, Url};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use thiserror::Error;

use crate::render_engine::{
    decode_image, validate_nine_sixteen, validate_render_request, RenderError, RenderJob,
    RenderProvider, RenderRequest, RenderState,
};

const TOKEN_URL: &str = "https://ims-na1.adobelogin.com/ims/token/v3";
const GENERATE_V3_ASYNC_URL: &str = "https://firefly-api.adobe.io/v3/images/generate-async";
const GENERATE_V4_IMAGE5_URL: &str = "https://firefly-api.adobe.io/v4/images/generate-async";
const FIREFLY_SCOPE: &str =
    "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis";
const MAX_HTTP_RETRIES: u32 = 3;
const MAX_RETRY_DELAY_SECONDS: u64 = 60;
const DEFAULT_POLL_INTERVAL_SECONDS: u64 = 15;
const DEFAULT_MAX_POLLS: u32 = 12;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AdobeApiProfile {
    V3Async,
    V4Image5,
}

impl AdobeApiProfile {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::V3Async => "v3_async",
            Self::V4Image5 => "v4_image5",
        }
    }

    fn endpoint(self) -> &'static str {
        match self {
            Self::V3Async => GENERATE_V3_ASYNC_URL,
            Self::V4Image5 => GENERATE_V4_IMAGE5_URL,
        }
    }

    fn parse(value: &str) -> Result<Self, AdobeProviderError> {
        match value {
            "v3_async" | "v3" => Ok(Self::V3Async),
            "v4_image5" | "v4" | "image5" => Ok(Self::V4Image5),
            other => Err(AdobeProviderError::InvalidProfile(other.to_string())),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AdobeExecutionDetails {
    pub api_profile: String,
    pub provider_job_id: String,
    pub output_host: String,
    pub seed: Option<u64>,
}

#[derive(Debug, Error)]
pub enum AdobeProviderError {
    #[error("missing Adobe Firefly credential: {0}")]
    MissingCredential(&'static str),
    #[error("invalid Adobe API profile: {0}")]
    InvalidProfile(String),
    #[error("Adobe transport error: {0}")]
    Transport(#[from] reqwest::Error),
    #[error("Adobe {stage} returned HTTP {status}")]
    UpstreamStatus { stage: &'static str, status: u16 },
    #[error("Adobe token response did not contain an access token")]
    MissingAccessToken,
    #[error("Adobe submission did not contain a job id")]
    MissingJobId,
    #[error("Adobe submission did not contain a status URL")]
    MissingStatusUrl,
    #[error("Adobe job failed")]
    JobFailed,
    #[error("Adobe job did not complete within the bounded polling window")]
    PollTimeout,
    #[error("Adobe response did not contain an image URL")]
    MissingImageUrl,
    #[error("Adobe image download returned empty bytes")]
    EmptyImage,
    #[error("blocked untrusted {kind} URL: {url}")]
    UnsafeUrl { kind: &'static str, url: String },
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
}

#[derive(Debug, Deserialize)]
struct AsyncSubmitResponse {
    #[serde(rename = "jobId")]
    job_id: String,
    #[serde(rename = "statusUrl")]
    status_url: String,
}

#[derive(Debug, Deserialize)]
struct AsyncStatusResponse {
    status: String,
    result: Option<GenerateResult>,
    outputs: Option<Vec<GenerateOutput>>,
}

#[derive(Debug, Deserialize)]
struct GenerateResult {
    outputs: Vec<GenerateOutput>,
}

#[derive(Debug, Deserialize)]
struct GenerateOutput {
    seed: Option<u64>,
    image: GeneratedImage,
}

#[derive(Debug, Deserialize)]
struct GeneratedImage {
    url: String,
}

struct CompletedOutput {
    image_url: String,
    seed: Option<u64>,
}

struct AdobeJobRecord {
    bytes: Vec<u8>,
    details: AdobeExecutionDetails,
}

pub struct AdobeRenderProvider {
    client: Client,
    client_id: String,
    client_secret: String,
    profile: AdobeApiProfile,
    poll_interval: Duration,
    max_polls: u32,
    jobs: Mutex<HashMap<String, AdobeJobRecord>>,
}

impl AdobeRenderProvider {
    pub fn from_env() -> Result<Self, AdobeProviderError> {
        let client_id = env::var("FIREFLY_SERVICES_CLIENT_ID")
            .map_err(|_| AdobeProviderError::MissingCredential("FIREFLY_SERVICES_CLIENT_ID"))?;
        let client_secret = env::var("FIREFLY_SERVICES_CLIENT_SECRET")
            .map_err(|_| AdobeProviderError::MissingCredential("FIREFLY_SERVICES_CLIENT_SECRET"))?;
        let profile = AdobeApiProfile::parse(
            &env::var("FIREFLY_API_PROFILE").unwrap_or_else(|_| "v3_async".to_string()),
        )?;
        let poll_interval_seconds = parse_env_u64(
            "FIREFLY_POLL_INTERVAL_SECONDS",
            DEFAULT_POLL_INTERVAL_SECONDS,
        );
        let max_polls = parse_env_u32("FIREFLY_MAX_POLLS", DEFAULT_MAX_POLLS);

        Self::with_profile(
            client_id,
            client_secret,
            profile,
            Duration::from_secs(poll_interval_seconds.max(DEFAULT_POLL_INTERVAL_SECONDS)),
            max_polls.max(1),
        )
    }

    pub fn new(client_id: String, client_secret: String) -> Result<Self, AdobeProviderError> {
        Self::with_profile(
            client_id,
            client_secret,
            AdobeApiProfile::V3Async,
            Duration::from_secs(DEFAULT_POLL_INTERVAL_SECONDS),
            DEFAULT_MAX_POLLS,
        )
    }

    pub fn with_profile(
        client_id: String,
        client_secret: String,
        profile: AdobeApiProfile,
        poll_interval: Duration,
        max_polls: u32,
    ) -> Result<Self, AdobeProviderError> {
        let client = Client::builder()
            .timeout(Duration::from_secs(60))
            .redirect(Policy::none())
            .build()?;
        Ok(Self {
            client,
            client_id,
            client_secret,
            profile,
            poll_interval,
            max_polls: max_polls.max(1),
            jobs: Mutex::new(HashMap::new()),
        })
    }

    pub fn profile(&self) -> AdobeApiProfile {
        self.profile
    }

    pub fn execution_details(&self, job_id: &str) -> Result<AdobeExecutionDetails, RenderError> {
        self.jobs
            .lock()
            .map_err(|_| RenderError::Provider("Adobe job cache lock poisoned".to_string()))?
            .get(job_id)
            .map(|record| record.details.clone())
            .ok_or_else(|| RenderError::Provider(format!("unknown Adobe render job: {job_id}")))
    }

    fn access_token(&self) -> Result<String, AdobeProviderError> {
        for attempt in 0..=MAX_HTTP_RETRIES {
            let response = self
                .client
                .post(TOKEN_URL)
                .form(&[
                    ("grant_type", "client_credentials"),
                    ("client_id", self.client_id.as_str()),
                    ("client_secret", self.client_secret.as_str()),
                    ("scope", FIREFLY_SCOPE),
                ])
                .send();

            match response {
                Ok(response) if response.status().is_success() => {
                    let token = response.json::<TokenResponse>()?.access_token;
                    if token.is_empty() {
                        return Err(AdobeProviderError::MissingAccessToken);
                    }
                    return Ok(token);
                }
                Ok(response) if retryable(response.status()) && attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(retry_delay(&response, attempt));
                }
                Ok(response) => {
                    return Err(AdobeProviderError::UpstreamStatus {
                        stage: "token endpoint",
                        status: response.status().as_u16(),
                    });
                }
                Err(_) if attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(exponential_delay(attempt));
                }
                Err(error) => return Err(AdobeProviderError::Transport(error)),
            }
        }
        Err(AdobeProviderError::PollTimeout)
    }

    fn submit_job(
        &self,
        request: &RenderRequest,
        access_token: &str,
    ) -> Result<AsyncSubmitResponse, AdobeProviderError> {
        let payload = request_payload(self.profile, request);

        for attempt in 0..=MAX_HTTP_RETRIES {
            let response = self
                .client
                .post(self.profile.endpoint())
                .bearer_auth(access_token)
                .header("x-api-key", &self.client_id)
                .header("Accept", "application/json")
                .json(&payload)
                .send();

            match response {
                Ok(response) if response.status().is_success() => {
                    let submission = response.json::<AsyncSubmitResponse>()?;
                    if submission.job_id.is_empty() {
                        return Err(AdobeProviderError::MissingJobId);
                    }
                    if submission.status_url.is_empty() {
                        return Err(AdobeProviderError::MissingStatusUrl);
                    }
                    validate_status_url(&submission.status_url)?;
                    return Ok(submission);
                }
                Ok(response) if retryable(response.status()) && attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(retry_delay(&response, attempt));
                }
                Ok(response) => {
                    return Err(AdobeProviderError::UpstreamStatus {
                        stage: "generation endpoint",
                        status: response.status().as_u16(),
                    });
                }
                Err(_) if attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(exponential_delay(attempt));
                }
                Err(error) => return Err(AdobeProviderError::Transport(error)),
            }
        }
        Err(AdobeProviderError::PollTimeout)
    }

    fn poll_job(
        &self,
        status_url: &str,
        access_token: &str,
    ) -> Result<CompletedOutput, AdobeProviderError> {
        validate_status_url(status_url)?;

        for poll in 0..self.max_polls {
            let response = self.authorized_get(status_url, access_token, "status endpoint")?;
            let body = response.json::<AsyncStatusResponse>()?;
            match body.status.to_ascii_lowercase().as_str() {
                "succeeded" => {
                    let outputs = body
                        .result
                        .map(|result| result.outputs)
                        .or(body.outputs)
                        .unwrap_or_default();
                    let output = outputs
                        .into_iter()
                        .next()
                        .ok_or(AdobeProviderError::MissingImageUrl)?;
                    if output.image.url.is_empty() {
                        return Err(AdobeProviderError::MissingImageUrl);
                    }
                    validate_output_url(&output.image.url)?;
                    return Ok(CompletedOutput {
                        image_url: output.image.url,
                        seed: output.seed,
                    });
                }
                "failed" | "cancelled" => return Err(AdobeProviderError::JobFailed),
                _ if poll + 1 < self.max_polls => thread::sleep(self.poll_interval),
                _ => return Err(AdobeProviderError::PollTimeout),
            }
        }
        Err(AdobeProviderError::PollTimeout)
    }

    fn authorized_get(
        &self,
        url: &str,
        access_token: &str,
        stage: &'static str,
    ) -> Result<Response, AdobeProviderError> {
        for attempt in 0..=MAX_HTTP_RETRIES {
            let response = self
                .client
                .get(url)
                .bearer_auth(access_token)
                .header("x-api-key", &self.client_id)
                .header("Accept", "application/json")
                .send();

            match response {
                Ok(response) if response.status().is_success() => return Ok(response),
                Ok(response) if retryable(response.status()) && attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(retry_delay(&response, attempt));
                }
                Ok(response) => {
                    return Err(AdobeProviderError::UpstreamStatus {
                        stage,
                        status: response.status().as_u16(),
                    });
                }
                Err(_) if attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(exponential_delay(attempt));
                }
                Err(error) => return Err(AdobeProviderError::Transport(error)),
            }
        }
        Err(AdobeProviderError::PollTimeout)
    }

    fn download_image(&self, url: &str) -> Result<Vec<u8>, AdobeProviderError> {
        validate_output_url(url)?;

        for attempt in 0..=MAX_HTTP_RETRIES {
            let response = self.client.get(url).send();
            match response {
                Ok(response) if response.status().is_success() => {
                    let bytes = response.bytes()?.to_vec();
                    if bytes.is_empty() {
                        return Err(AdobeProviderError::EmptyImage);
                    }
                    return Ok(bytes);
                }
                Ok(response) if retryable(response.status()) && attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(retry_delay(&response, attempt));
                }
                Ok(response) => {
                    return Err(AdobeProviderError::UpstreamStatus {
                        stage: "image download",
                        status: response.status().as_u16(),
                    });
                }
                Err(_) if attempt < MAX_HTTP_RETRIES => {
                    thread::sleep(exponential_delay(attempt));
                }
                Err(error) => return Err(AdobeProviderError::Transport(error)),
            }
        }
        Err(AdobeProviderError::PollTimeout)
    }

    fn map_error(error: AdobeProviderError) -> RenderError {
        RenderError::Provider(error.to_string())
    }
}

impl RenderProvider for AdobeRenderProvider {
    fn submit(&self, request: &RenderRequest) -> Result<RenderJob, RenderError> {
        validate_render_request(request)
            .map_err(|error| RenderError::Rejected(error.to_string()))?;
        let access_token = self.access_token().map_err(Self::map_error)?;
        let submission = self
            .submit_job(request, &access_token)
            .map_err(Self::map_error)?;
        let output = self
            .poll_job(&submission.status_url, &access_token)
            .map_err(Self::map_error)?;
        let bytes = self
            .download_image(&output.image_url)
            .map_err(Self::map_error)?;

        let decoded = decode_image(bytes.clone())?;
        validate_nine_sixteen(&decoded)?;
        let output_host = validate_output_url(&output.image_url).map_err(Self::map_error)?;
        let job_id = submission.job_id;
        let details = AdobeExecutionDetails {
            api_profile: self.profile.as_str().to_string(),
            provider_job_id: job_id.clone(),
            output_host,
            seed: output.seed,
        };

        self.jobs
            .lock()
            .map_err(|_| RenderError::Provider("Adobe job cache lock poisoned".to_string()))?
            .insert(job_id.clone(), AdobeJobRecord { bytes, details });

        Ok(RenderJob {
            job_id,
            state: RenderState::ProviderSuccess,
        })
    }

    fn status(&self, job_id: &str) -> Result<RenderState, RenderError> {
        let jobs = self
            .jobs
            .lock()
            .map_err(|_| RenderError::Provider("Adobe job cache lock poisoned".to_string()))?;
        Ok(if jobs.contains_key(job_id) {
            RenderState::ProviderSuccess
        } else {
            RenderState::ProviderFailure
        })
    }

    fn fetch(&self, job_id: &str) -> Result<Vec<u8>, RenderError> {
        self.jobs
            .lock()
            .map_err(|_| RenderError::Provider("Adobe job cache lock poisoned".to_string()))?
            .get(job_id)
            .map(|record| record.bytes.clone())
            .ok_or_else(|| RenderError::Provider(format!("unknown Adobe render job: {job_id}")))
    }
}

fn request_payload(profile: AdobeApiProfile, request: &RenderRequest) -> Value {
    match profile {
        AdobeApiProfile::V3Async => json!({
            "prompt": request.prompt.as_str(),
            "size": {
                "width": request.width,
                "height": request.height
            },
            "numVariations": 1,
            "promptBiasingLocaleCode": "en-US"
        }),
        AdobeApiProfile::V4Image5 => json!({
            "prompt": request.prompt.as_str(),
            "aspectRatio": "9:16",
            "modelId": "firefly_image",
            "numVariations": 1,
            "referenceBlobs": [],
            "modelSpecificPayload": {
                "localeCode": "en-US",
                "prompt_reasoner": "quality"
            }
        }),
    }
}

fn validate_status_url(url: &str) -> Result<String, AdobeProviderError> {
    validate_https_url(url, "status", &["adobe.io"])
}

fn validate_output_url(url: &str) -> Result<String, AdobeProviderError> {
    validate_https_url(
        url,
        "output",
        &[
            "amazonaws.com",
            "windows.net",
            "dropboxusercontent.com",
            "storage.googleapis.com",
            "frontdoor.prod.azure.cxp.adobe.com",
            "adobe.io",
        ],
    )
}

fn validate_https_url(
    raw_url: &str,
    kind: &'static str,
    allowed_domains: &[&str],
) -> Result<String, AdobeProviderError> {
    let parsed = Url::parse(raw_url).map_err(|_| AdobeProviderError::UnsafeUrl {
        kind,
        url: raw_url.to_string(),
    })?;
    let host = parsed
        .host_str()
        .ok_or_else(|| AdobeProviderError::UnsafeUrl {
            kind,
            url: raw_url.to_string(),
        })?;
    let allowed = parsed.scheme() == "https"
        && allowed_domains
            .iter()
            .any(|domain| domain_matches(host, domain));
    if !allowed {
        return Err(AdobeProviderError::UnsafeUrl {
            kind,
            url: raw_url.to_string(),
        });
    }
    Ok(host.to_string())
}

fn domain_matches(host: &str, allowed: &str) -> bool {
    host == allowed
        || host
            .strip_suffix(allowed)
            .is_some_and(|prefix| prefix.ends_with('.'))
}

fn retryable(status: StatusCode) -> bool {
    status == StatusCode::TOO_MANY_REQUESTS || status.is_server_error()
}

fn retry_delay(response: &Response, attempt: u32) -> Duration {
    response
        .headers()
        .get(RETRY_AFTER)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.parse::<u64>().ok())
        .map(|seconds| Duration::from_secs(seconds.min(MAX_RETRY_DELAY_SECONDS)))
        .unwrap_or_else(|| exponential_delay(attempt))
}

fn exponential_delay(attempt: u32) -> Duration {
    Duration::from_secs(1u64 << attempt.min(5))
}

fn parse_env_u64(name: &str, default: u64) -> u64 {
    env::var(name)
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or(default)
}

fn parse_env_u32(name: &str, default: u32) -> u32 {
    env::var(name)
        .ok()
        .and_then(|value| value.parse::<u32>().ok())
        .unwrap_or(default)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request() -> RenderRequest {
        RenderRequest {
            prompt: "Black Onyx and Platinum portrait".to_string(),
            width: 1080,
            height: 1920,
        }
    }

    #[test]
    fn provider_construction_does_not_require_network_access() {
        let provider = AdobeRenderProvider::new("client-id".to_string(), "secret".to_string());
        assert!(provider.is_ok());
    }

    #[test]
    fn missing_job_is_not_reported_as_success() {
        let provider = AdobeRenderProvider::new("client-id".to_string(), "secret".to_string())
            .expect("client construction should not require network access");
        assert_eq!(
            provider.status("missing-job").unwrap(),
            RenderState::ProviderFailure
        );
        assert!(provider.fetch("missing-job").is_err());
    }

    #[test]
    fn v3_and_image5_payloads_are_explicitly_versioned() {
        let v3 = request_payload(AdobeApiProfile::V3Async, &request());
        let v4 = request_payload(AdobeApiProfile::V4Image5, &request());

        assert_eq!(v3["size"]["width"], 1080);
        assert_eq!(v3["size"]["height"], 1920);
        assert_eq!(v4["aspectRatio"], "9:16");
        assert_eq!(v4["modelId"], "firefly_image");
        assert_eq!(v4["numVariations"], 1);
    }

    #[test]
    fn status_and_output_urls_are_fail_closed() {
        assert!(validate_status_url("https://firefly-epo.adobe.io/v3/status/job").is_ok());
        assert!(validate_status_url("http://firefly-epo.adobe.io/v3/status/job").is_err());
        assert!(validate_status_url("https://evil.example/status/job").is_err());

        assert!(validate_output_url(
            "https://pre-signed-firefly-prod.s3-accelerate.amazonaws.com/image.png"
        )
        .is_ok());
        assert!(validate_output_url("https://amazonaws.com.evil.example/image.png").is_err());
    }

    #[test]
    fn unknown_profile_is_rejected() {
        assert!(matches!(
            AdobeApiProfile::parse("future_unverified"),
            Err(AdobeProviderError::InvalidProfile(_))
        ));
    }
}
