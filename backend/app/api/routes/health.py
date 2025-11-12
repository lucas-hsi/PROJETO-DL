from fastapi import APIRouter
from fastapi import Request
from app.core.config import get_settings

router = APIRouter()


@router.get("/healthz")
def healthz(request: Request):
    settings = get_settings()
    start_time = getattr(request.app.state, "start_time", None)
    uptime = None
    if start_time:
        from time import time
        uptime = round(time() - start_time, 3)

    return {
        "status": "ok",
        "uptime": uptime,
        "version": settings.APP_VERSION,
    }