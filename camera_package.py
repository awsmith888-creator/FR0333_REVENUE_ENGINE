from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CAMERA_PACKAGE_VERSION = "FR0333-CAMERA-PACKAGE-v2.0.0"
UNIT_SYSTEM = "SI_METRIC"
TARGET_ASPECT_RATIO = 9 / 16


class CameraCaptureSpec(BaseModel):
    """Deterministic camera/edit job specification using SI/metric units only."""

    model_config = ConfigDict(extra="forbid")

    source_ids: list[str] = Field(min_length=1, max_length=1)
    source_people_observed: int | None = Field(default=None, ge=0)
    expected_people_output: int | None = Field(default=None, ge=0)

    output_width_px: int = Field(default=1080, gt=0)
    output_height_px: int = Field(default=1920, gt=0)
    orientation: Literal["portrait"] = "portrait"

    preserve_composition: bool = True
    remove_interface_overlays: bool = True
    allow_subject_carry_from_previous_job: bool = False
    add_unseen_subject: bool = False

    # Metric / SI camera and scene metadata.
    focal_length_mm: float | None = Field(default=None, gt=0)
    sensor_width_mm: float | None = Field(default=None, gt=0)
    sensor_height_mm: float | None = Field(default=None, gt=0)
    focus_distance_m: float | None = Field(default=None, gt=0)
    subject_distance_m: float | None = Field(default=None, gt=0)
    camera_height_m: float | None = Field(default=None, ge=0)
    translation_tolerance_mm: float | None = Field(default=None, ge=0)
    angular_tolerance_rad: float | None = Field(default=None, ge=0)
    exposure_time_s: float | None = Field(default=None, gt=0)
    color_temperature_K: float | None = Field(default=None, gt=0)
    illuminance_lx: float | None = Field(default=None, ge=0)

    # Imaging quantities that are dimensionless or count-based by definition.
    aperture_f_number: float | None = Field(default=None, gt=0)
    iso_index: int | None = Field(default=None, gt=0)
    frame_rate_hz: float | None = Field(default=None, gt=0)

    unit_system: Literal["SI_METRIC"] = UNIT_SYSTEM

    @model_validator(mode="after")
    def validate_image_contract(self) -> "CameraCaptureSpec":
        ratio = self.output_width_px / self.output_height_px
        if abs(ratio - TARGET_ASPECT_RATIO) > 1e-9:
            raise ValueError("output dimensions must be exact 9:16 portrait ratio")

        if self.allow_subject_carry_from_previous_job:
            raise ValueError(
                "subject carry from a previous job is blocked; each output is source-isolated"
            )

        if self.source_people_observed is not None and self.expected_people_output is not None:
            if self.source_people_observed != self.expected_people_output and not self.add_unseen_subject:
                raise ValueError(
                    "people-count mismatch: output may not invent or remove people without an explicit edit request"
                )

        if self.source_people_observed == 0 and self.expected_people_output not in (None, 0):
            if not self.add_unseen_subject:
                raise ValueError("source has no people; adding a person requires add_unseen_subject=true")

        return self


class CameraValidationResult(BaseModel):
    package_version: str = CAMERA_PACKAGE_VERSION
    status: Literal["PASS", "REJECT"]
    unit_system: Literal["SI_METRIC"] = UNIT_SYSTEM
    normalized: dict[str, Any] | None = None
    faults: list[str] = []


def validate_camera_job(payload: dict[str, Any]) -> CameraValidationResult:
    try:
        spec = CameraCaptureSpec.model_validate(payload)
        return CameraValidationResult(
            status="PASS",
            normalized=spec.model_dump(mode="json", exclude_none=True),
            faults=[],
        )
    except Exception as exc:
        return CameraValidationResult(status="REJECT", faults=[str(exc)])


def package_manifest() -> dict[str, Any]:
    return {
        "package_version": CAMERA_PACKAGE_VERSION,
        "unit_system": UNIT_SYSTEM,
        "aspect_ratio": "9:16",
        "orientation": "portrait",
        "source_isolation": "ONE_SOURCE_IMAGE_PER_OUTPUT",
        "subject_carry": "BLOCKED_BY_DEFAULT",
        "unseen_subject_insertion": "BLOCKED_BY_DEFAULT",
        "overlay_removal_default": True,
        "composition_preservation_default": True,
        "metric_fields": {
            "length_small": "mm",
            "distance": "m",
            "time": "s",
            "angle": "rad",
            "temperature": "K",
            "illuminance": "lx",
            "frame_rate": "Hz",
            "resolution": "px",
        },
        "dimensionless_fields": ["aperture_f_number", "iso_index", "aspect_ratio"],
    }
