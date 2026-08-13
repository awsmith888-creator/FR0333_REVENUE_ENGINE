use image::{guess_format, load_from_memory, GenericImageView, ImageFormat};
use sha2::{Digest, Sha256};
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

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactReceipt {
    pub sha256: [u8; 32],
    pub byte_len: u64,
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
    #[error("image dimensions are not 9:16: {width}x{height}")]
    InvalidAspectRatio { width: u32, height: u32 },
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
    let decoded =
        load_from_memory(&bytes).map_err(|error| RenderError::Decode(error.to_string()))?;
    let (width, height) = decoded.dimensions();
    Ok(DecodedImage {
        bytes,
        width,
        height,
        media_type,
    })
}

pub fn validate_nine_sixteen(image: &DecodedImage) -> Result<(), RenderError> {
    if u64::from(image.width) * 16 != u64::from(image.height) * 9 {
        return Err(RenderError::InvalidAspectRatio {
            width: image.width,
            height: image.height,
        });
    }
    Ok(())
}

pub fn artifact_receipt(image: &DecodedImage) -> Result<ArtifactReceipt, RenderError> {
    validate_nine_sixteen(image)?;
    let digest = Sha256::digest(&image.bytes);
    let mut sha256 = [0u8; 32];
    sha256.copy_from_slice(&digest);
    Ok(ArtifactReceipt {
        sha256,
        byte_len: image.bytes.len() as u64,
        width: image.width,
        height: image.height,
        media_type: image.media_type,
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
    use super::*;
    use image::{DynamicImage, ImageFormat, RgbaImage};
    use std::io::Cursor;

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
        assert_eq!((decoded.width, decoded.height), (9, 16));
        assert_eq!(decoded.media_type, "image/png");
        assert!(!decoded.bytes.is_empty());
    }

    #[test]
    fn empty_provider_payload_is_held_as_error() {
        let provider = MemoryProvider { bytes: Vec::new() };
        assert!(matches!(
            fetch_and_decode(&provider, "memory-job-1"),
            Err(RenderError::EmptyBytes)
        ));
    }

    #[test]
    fn invalid_payload_does_not_promote_to_decoded_image() {
        let result = decode_image(b"not an image".to_vec());
        assert!(matches!(
            result,
            Err(RenderError::UnsupportedImageFormat) | Err(RenderError::Decode(_))
        ));
    }

    #[test]
    fn exact_nine_sixteen_produces_sha256_receipt() {
        let decoded = decode_image(png_bytes(90, 160)).unwrap();
        let receipt = artifact_receipt(&decoded).unwrap();
        assert_eq!((receipt.width, receipt.height), (90, 160));
        assert_eq!(receipt.byte_len, decoded.bytes.len() as u64);
        assert_eq!(receipt.sha256.len(), 32);
    }

    #[test]
    fn non_nine_sixteen_is_held() {
        let decoded = decode_image(png_bytes(100, 100)).unwrap();
        assert!(matches!(
            artifact_receipt(&decoded),
            Err(RenderError::InvalidAspectRatio { .. })
        ));
    }

    #[test]
    fn one_byte_change_changes_artifact_hash() {
        let first = decode_image(png_bytes(90, 160)).unwrap();
        let mut second_bytes = first.bytes.clone();
        let last = second_bytes.len() - 1;
        second_bytes[last] ^= 1;
        let first_hash = Sha256::digest(&first.bytes);
        let second_hash = Sha256::digest(&second_bytes);
        assert_ne!(first_hash[..], second_hash[..]);
    }
}
