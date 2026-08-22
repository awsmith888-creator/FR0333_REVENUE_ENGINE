from fastapi import FastAPI, Query, Request, Response, status

from camera_package import CameraCaptureSpec, package_manifest, validate_camera_job
from facebook_bridge import (
    bridge_manifest,
    ingest_webhook,
    recent_events,
    verify_webhook_subscription,
)

app = FastAPI(title="FR0333 Revenue Engine Pipeline")


@app.get("/healthz", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "ACTIVE",
        "lane_check": "LANE_3_PHYSICAL_DEPLOYMENT_PENDING",
        "receipt_anchor": "3e65819c1e4998397e92d8a917b9c13d2cccbc085ccdc5b3a633f29014399630",
        "camera_package": package_manifest()["package_version"],
        "facebook_bridge": bridge_manifest()["bridge_version"],
        "unit_system": "SI_METRIC",
    }


@app.get("/camera/package", status_code=status.HTTP_200_OK)
def get_camera_package():
    return package_manifest()


@app.post("/camera/validate", status_code=status.HTTP_200_OK)
def validate_camera_capture(spec: CameraCaptureSpec):
    return validate_camera_job(spec.model_dump(mode="json"))


@app.get("/facebook/status", status_code=status.HTTP_200_OK)
def facebook_status():
    return bridge_manifest()


@app.get("/facebook/webhook", status_code=status.HTTP_200_OK)
def facebook_webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    challenge = verify_webhook_subscription(hub_mode, hub_verify_token, hub_challenge)
    return Response(content=challenge, media_type="text/plain")


@app.post("/facebook/webhook", status_code=status.HTTP_200_OK)
async def facebook_webhook_ingest(request: Request):
    return await ingest_webhook(request)


@app.get("/facebook/events", status_code=status.HTTP_200_OK)
def facebook_events(limit: int = Query(default=25, ge=1, le=100)):
    return recent_events(limit)
