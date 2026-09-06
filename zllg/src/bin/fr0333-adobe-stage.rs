use std::env;
use std::error::Error;
use std::fs;
use std::io::{Cursor, Error as IoError, ErrorKind};
use std::path::{Component, Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

use image::{DynamicImage, ImageFormat, Rgba, RgbaImage};
use zllg::adobe_alignment::{
    build_alignment_receipt, AlignmentReceiptInput, ContentCredentialsState, ExecutionMode,
    ProviderObservation, MASTER_HEIGHT, MASTER_WIDTH,
};
use zllg::adobe_provider::AdobeRenderProvider;
use zllg::render_engine::{
    artifact_receipt, decode_image, fetch_and_decode, RenderProvider, RenderRequest, RenderState,
};

const REFERENCE_ID: &str = "FR0333-ADOBE-STAGE-000001";

fn main() {
    if let Err(error) = run() {
        eprintln!("FR0333_ADOBE_STAGE=FAILED: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let (mode, output_root) = parse_args()?;
    validate_output_root(&output_root)?;

    if mode == ExecutionMode::LiveStaging
        && env::var("FR0333_ALLOW_LIVE_ADOBE").as_deref() != Ok("STAGING_ONLY")
    {
        return Err(invalid_input(
            "live Adobe execution requires FR0333_ALLOW_LIVE_ADOBE=STAGING_ONLY",
        ));
    }

    let commit_sha = env::var("GITHUB_SHA")
        .or_else(|_| env::var("FR0333_COMMIT_SHA"))
        .unwrap_or_else(|_| "LOCAL_UNCOMMITTED_SIMULATION".to_string());
    if mode == ExecutionMode::LiveStaging && commit_sha == "LOCAL_UNCOMMITTED_SIMULATION" {
        return Err(invalid_input(
            "live Adobe execution requires GITHUB_SHA or FR0333_COMMIT_SHA",
        ));
    }

    let request = RenderRequest {
        prompt: env::var("FR0333_ADOBE_PROMPT").unwrap_or_else(|_| {
            "A dignified Black Onyx and Platinum editorial study, vertical composition, no text, no logos"
                .to_string()
        }),
        width: MASTER_WIDTH,
        height: MASTER_HEIGHT,
    };

    let (decoded, provider, content_credentials) = match mode {
        ExecutionMode::Simulation => (
            decode_image(simulation_png()?)?,
            ProviderObservation {
                api_profile: "simulation_memory_provider".to_string(),
                provider_job_id: "simulation-job-1".to_string(),
                output_host: "local-sandbox".to_string(),
                seed: None,
            },
            ContentCredentialsState::NotApplicable,
        ),
        ExecutionMode::LiveStaging => {
            let adobe = AdobeRenderProvider::from_env()?;
            let job = adobe.submit(&request)?;
            if job.state != RenderState::ProviderSuccess {
                return Err(invalid_input("Adobe job did not reach provider success"));
            }
            let decoded = fetch_and_decode(&adobe, &job.job_id)?;
            let details = adobe.execution_details(&job.job_id)?;
            (
                decoded,
                ProviderObservation {
                    api_profile: details.api_profile,
                    provider_job_id: details.provider_job_id,
                    output_host: details.output_host,
                    seed: details.seed,
                },
                ContentCredentialsState::NotInspected,
            )
        }
    };

    let artifact = artifact_receipt(&decoded)?;
    let observed_at_unix = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let receipt = build_alignment_receipt(AlignmentReceiptInput {
        reference_id: REFERENCE_ID,
        execution_mode: mode,
        observed_at_unix,
        commit_sha: &commit_sha,
        request: &request,
        artifact: &artifact,
        provider,
        content_credentials,
    });

    fs::create_dir_all(&output_root)?;
    let extension = match artifact.media_type {
        "image/png" => "png",
        "image/jpeg" => "jpg",
        other => {
            return Err(invalid_input(format!(
                "unsupported output media type: {other}"
            )))
        }
    };
    let artifact_path = output_root.join(format!("artifact.{extension}"));
    let receipt_path = output_root.join("alignment-receipt.json");
    fs::write(&artifact_path, &decoded.bytes)?;
    fs::write(&receipt_path, serde_json::to_vec_pretty(&receipt)?)?;

    println!("FR0333_ADOBE_STAGE=RECEIPTED");
    println!("EXECUTION_MODE={:?}", receipt.execution_mode);
    println!("ARTIFACT_SHA256={}", receipt.artifact_sha256);
    println!(
        "GEOMETRY={}x{}",
        receipt.artifact_width, receipt.artifact_height
    );
    println!("STAGING_READY={}", receipt.release_gates.staging_ready);
    println!("PUBLICITY_READY={}", receipt.release_gates.publicity_ready);
    println!("MERGE_READY={}", receipt.release_gates.merge_ready);
    println!(
        "PRODUCTION_READY={}",
        receipt.release_gates.production_ready
    );

    if mode == ExecutionMode::LiveStaging && !receipt.release_gates.staging_ready {
        return Err(invalid_input(
            "live artifact was receipted but did not pass the staging gate",
        ));
    }
    Ok(())
}

fn parse_args() -> Result<(ExecutionMode, PathBuf), Box<dyn Error>> {
    let mut mode = None;
    let mut output = PathBuf::from("target/fr0333-staging");
    let mut args = env::args().skip(1);

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--simulate" if mode.is_none() => mode = Some(ExecutionMode::Simulation),
            "--live" if mode.is_none() => mode = Some(ExecutionMode::LiveStaging),
            "--simulate" | "--live" => {
                return Err(invalid_input("select exactly one execution mode"));
            }
            "--output" => {
                output = PathBuf::from(
                    args.next()
                        .ok_or_else(|| invalid_input("--output requires a path"))?,
                );
            }
            other => return Err(invalid_input(format!("unknown argument: {other}"))),
        }
    }

    Ok((
        mode.ok_or_else(|| invalid_input("use --simulate or --live"))?,
        output,
    ))
}

fn validate_output_root(path: &Path) -> Result<(), Box<dyn Error>> {
    if path.is_absolute()
        || path
            .components()
            .any(|component| matches!(component, Component::ParentDir | Component::RootDir))
    {
        return Err(invalid_input(
            "output path must be a relative path without parent traversal",
        ));
    }
    Ok(())
}

fn simulation_png() -> Result<Vec<u8>, Box<dyn Error>> {
    let image = RgbaImage::from_pixel(MASTER_WIDTH, MASTER_HEIGHT, Rgba([0, 0, 0, 255]));
    let mut cursor = Cursor::new(Vec::new());
    DynamicImage::ImageRgba8(image).write_to(&mut cursor, ImageFormat::Png)?;
    Ok(cursor.into_inner())
}

fn invalid_input(message: impl Into<String>) -> Box<dyn Error> {
    Box::new(IoError::new(ErrorKind::InvalidInput, message.into()))
}
