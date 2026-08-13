use image::{guess_format, load_from_memory, GenericImageView, ImageFormat};
use thiserror::Error;

pub type ArtifactId = [u8; 16];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderRequest {
    pub prompt: String,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RenderJob {
    pub job_id: String,
    pub state: RenderState,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RenderState {
    Requested,
    Accepted,
    Rendering,
    ProviderSuccess,
    ProviderFailure,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodedImage {
    pub bytes: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub media_type: &'static str,
}

#[derive(Debug, Error)]
pub enum RenderError {
    #[error("render provider rejected the request: {0}")]
    Rejected(String),

    #[error("render provider failed: {0}")]
    Provider(String),

    #[error("render provider returned empty image bytes")]
    EmptyBytes,

    #[error("unsupported image format")]
    UnsupportedImageFormat,

    #[error("image decode failed: {0}")]
    Decode(String),
}

pub trait RenderProvider {
    fn submit(&self, request: &RenderRequest) -> Result<RenderJob, RenderError>;

    fn status(&self, job_id: &str) -> Result<RenderState, RenderError>;

    fn fetch(&self, job_id: &str) -> Result<Vec<u8>, RenderError>;
}

pub fn fetch_and_decode<P: RenderProvider>(
    provider: &P,
    job_id: &str,
) -> Result<DecodedImage, RenderError> {
    let bytes = provider.fetch(job_id)?;
    decode_image(bytes)
}

pub fn decode_image(bytes: Vec<u8>) -> Result<DecodedImage, RenderError> {
    if bytes.is_empty() {
        return Err(RenderError::EmptyBytes);
    }

    let format = guess_format(&bytes).map_err(|_| RenderError::UnsupportedImageFormat)?;
    let media_type = media_type_for(format).ok_or(RenderError::UnsupportedImageFormat)?;

    let decoded = load_from_memory(&bytes).map_err(|error| RenderError::Decode(error.to_string()))?;
    let (width, height) = decoded.dimensions();

    Ok(DecodedImage {
        bytes,
        width,
        height,
        media_type,
    })
}

fn media_type_for(format: ImageFormat) -> Option<&'static str> {
    match format {
        ImageFormat::Png => Some("image/png"),
        ImageFormat::Jpeg => Some("image/jpeg"),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use image::{DynamicImage, ImageFormat, RgbaImage};

    use super::*;

    struct MemoryProvider {
        bytes: Vec<u8>,
    }

    impl RenderProvider for MemoryProvider {
        fn submit(&self, _request: &RenderRequest) -> Result<RenderJob, RenderError> {
            Ok(RenderJob {
                job_id: "memory-job-1".to_string(),
                state: RenderState::Accepted,
            })
        }

        fn status(&self, _job_id: &str) -> Result<RenderState, RenderError> {
            Ok(RenderState::ProviderSuccess)
        }

        fn fetch(&self, _job_id: &str) -> Result<Vec<u8>, RenderError> {
            Ok(self.bytes.clone())
        }
    }

    fn png_bytes(width: u32, height: u32) -> Vec<u8> {
        let image = DynamicImage::ImageRgba8(RgbaImage::new(width, height));
        let mut cursor = Cursor::new(Vec::new());
        image.write_to(&mut cursor, ImageFormat::Png).unwrap();
        cursor.into_inner()
    }

    #[test]
    fn provider_contract_fetches_and_decodes_real_image_bytes() {
        let provider = MemoryProvider {
            bytes: png_bytes(9, 16),
        };

        let decoded = fetch_and_decode(&provider, "memory-job-1").unwrap();

        assert_eq!(decoded.width, 9);
        assert_eq!(decoded.height, 16);
        assert_eq!(decoded.media_type, "image/png");
        assert!(!decoded.bytes.is_empty());
    }

    #[test]
    fn empty_provider_payload_is_held_as_error() {
        let provider = MemoryProvider { bytes: Vec::new() };

        let result = fetch_and_decode(&provider, "memory-job-1");

        assert!(matches!(result, Err(RenderError::EmptyBytes)));
    }

    #[test]
    fn invalid_payload_does_not_promote_to_decoded_image() {
        let result = decode_image(b"not an image".to_vec());

        assert!(matches!(
            result,
            Err(RenderError::UnsupportedImageFormat) | Err(RenderError::Decode(_))
        ));
    }
}
