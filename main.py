from fastapi import FastAPI, status

from camera_package import CameraCaptureSpec, package_manifest, validate_camera_job

app = FastAPI(title="FR0333 Revenue Engine Pipeline")


@app.get("/healthz", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "ACTIVE",
        "lane_check": "LANE_3_PHYSICAL_DEPLOYMENT_PENDING",
        "receipt_anchor": "3e65819c1e4998397e92d8a917b9c13d2cccbc085ccdc5b3a633f29014399630",
        "camera_package": package_manifest()["package_version"],
        "unit_system": "SI_METRIC",
    }


@app.get("/camera/package", status_code=status.HTTP_200_OK)
def get_camera_package():
    return package_manifest()


@app.post("/camera/validate", status_code=status.HTTP_200_OK)
def validate_camera_capture(spec: CameraCaptureSpec):
    return validate_camera_job(spec.model_dump(mode="json"))
