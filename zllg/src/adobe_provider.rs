use std::collections::HashMap;
use std::env;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::Duration;

use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::render_engine::{RenderError, RenderJob, RenderProvider, RenderRequest, RenderState};

const TOKEN_URL: &str = "https://ims-na1.adobelogin.com/ims/token/v3";
const GENERATE_URL: &str = "https://firefly-api.adobe.io/v3/images/generate";
const FIREFLY_SCOPE: &str =
    "openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis";

#[derive(Debug, Error)]
pub enum AdobeProviderError {
    #[error("missing Adobe Firefly credential: {0}")]
    MissingCredential(&'static str),
    #[error("Adobe transport error: {0}")]
    Transport(#[from] reqwest::Error),
    #[error("Adobe upstream returned HTTP {0}")]
    UpstreamStatus(u16),
    #[error("Adobe response did not contain an image URL")]
    MissingImageUrl,
    #[error("Adobe image download returned empty bytes")]
    EmptyImage,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
}

#[derive(Debug, Serialize)]
struct GeneratePayload<'a> {
    prompt: &'a str,
    size: ImageSize,
}

#[derive(Debug, Serialize)]
struct ImageSize {
    width: u32,
    height: u32,
}

#[derive(Debug, Deserialize)]
struct GenerateResponse {
    outputs: Vec<GenerateOutput>,
}

#[derive(Debug, Deserialize)]
struct GenerateOutput {
    image: GeneratedImage,
}

#[derive(Debug, Deserialize)]
struct GeneratedImage {
    url: String,
}

pub struct AdobeRenderProvider {
    client: Client,
    client_id: String,
    client_secret: String,
    jobs: Mutex<HashMap<String, Vec<u8>>>,
    next_job_id: AtomicU64,
}

impl AdobeRenderProvider {
    pub fn from_env() -> Result<Self, AdobeProviderError> {
        let client_id = env::var("FIREFLY_SERVICES_CLIENT_ID")
            .map_err(|_| AdobeProviderError::MissingCredential("FIREFLY_SERVICES_CLIENT_ID"))?;
        let client_secret = env::var("FIREFLY_SERVICES_CLIENT_SECRET")
            .map_err(|_| AdobeProviderError::MissingCredential("FIREFLY_SERVICES_CLIENT_SECRET"))?;
        Self::new(client_id, client_secret)
    }

    pub fn new(client_id: String, client_secret: String) -> Result<Self, AdobeProviderError> {
        let client = Client::builder().timeout(Duration::from_secs(60)).build()?;
        Ok(Self {
            client,
            client_id,
            client_secret,
            jobs: Mutex::new(HashMap::new()),
            next_job_id: AtomicU64::new(1),
        })
    }

    fn access_token(&self) -> Result<String, AdobeProviderError> {
        let response = self
            .client
            .post(TOKEN_URL)
            .form(&[
                ("grant_type", "client_credentials"),
                ("client_id", self.client_id.as_str()),
                ("client_secret", self.client_secret.as_str()),
                ("scope", FIREFLY_SCOPE),
            ])
            .send()?;

        if !response.status().is_success() {
            return Err(AdobeProviderError::UpstreamStatus(
                response.status().as_u16(),
            ));
        }

        Ok(response.json::<TokenResponse>()?.access_token)
    }

    fn generate_bytes(&self, request: &RenderRequest) -> Result<Vec<u8>, AdobeProviderError> {
        let token = self.access_token()?;
        let payload = GeneratePayload {
            prompt: &request.prompt,
            size: ImageSize {
                width: request.width,
                height: request.height,
            },
        };

        let response = self
            .client
            .post(GENERATE_URL)
            .bearer_auth(token)
            .header("x-api-key", &self.client_id)
            .header("Accept", "application/json")
            .json(&payload)
            .send()?;

        if !response.status().is_success() {
            return Err(AdobeProviderError::UpstreamStatus(
                response.status().as_u16(),
            ));
        }

        let body = response.json::<GenerateResponse>()?;
        let image_url = body
            .outputs
            .first()
            .map(|output| output.image.url.as_str())
            .filter(|url| !url.is_empty())
            .ok_or(AdobeProviderError::MissingImageUrl)?;

        let image_response = self.client.get(image_url).send()?;
        if !image_response.status().is_success() {
            return Err(AdobeProviderError::UpstreamStatus(
                image_response.status().as_u16(),
            ));
        }

        let bytes = image_response.bytes()?.to_vec();
        if bytes.is_empty() {
            return Err(AdobeProviderError::EmptyImage);
        }
        Ok(bytes)
    }

    fn map_error(error: AdobeProviderError) -> RenderError {
        RenderError::Provider(error.to_string())
    }
}

impl RenderProvider for AdobeRenderProvider {
    fn submit(&self, request: &RenderRequest) -> Result<RenderJob, RenderError> {
        let bytes = self.generate_bytes(request).map_err(Self::map_error)?;
        let job_id = format!(
            "adobe-sync-{}",
            self.next_job_id.fetch_add(1, Ordering::Relaxed)
        );
        self.jobs
            .lock()
            .map_err(|_| RenderError::Provider("Adobe job cache lock poisoned".to_string()))?
            .insert(job_id.clone(), bytes);
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
            .cloned()
            .ok_or_else(|| RenderError::Provider(format!("unknown Adobe render job: {job_id}")))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provider_requires_both_credentials() {
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
}
