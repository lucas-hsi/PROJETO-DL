import os
import requests
from fastapi import APIRouter, Query
from app.core.config import get_settings
from app.services.mercadolivre_service import meli_request, MeliAuthError

router = APIRouter(prefix="/diagnostics/meli")


@router.get("/config")
def meli_config():
    settings = get_settings()
    has_access = bool(getattr(settings, "ML_ACCESS_TOKEN", ""))
    has_refresh = bool(getattr(settings, "ML_REFRESH_TOKEN", ""))
    return {
        "seller_id": getattr(settings, "ML_SELLER_ID", None),
        "base_url": getattr(settings, "ML_API_BASE_URL", "https://api.mercadolibre.com"),
        "has_access_token": has_access,
        "has_refresh_token": has_refresh,
    }


@router.get("/whoami")
async def meli_whoami():
    try:
        data = await meli_request("GET", "/users/me")
        return {
            "status_code": 200,
            "user_id": data.get("id"),
            "nickname": data.get("nickname"),
            "site_id": data.get("site_id"),
            "scopes": data.get("scopes") if isinstance(data.get("scopes"), list) else None,
        }
    except MeliAuthError as e:
        return {"status_code": e.status, "user_id": None, "nickname": None, "site_id": None, "scopes": None}


@router.get("/items-sample")
async def meli_items_sample(limit: int = Query(5, ge=1, le=50)):
    settings = get_settings()
    try:
        payload = await meli_request("GET", f"/users/{settings.ML_SELLER_ID}/items/search", params={"status": "active", "limit": limit})
        total = int(payload.get("paging", {}).get("total", 0))
        sample_ids = payload.get("results", [])[:limit]
        return {"status_code": 200, "total": total, "sample_ids": sample_ids}
    except MeliAuthError as e:
        return {"status_code": e.status, "total": 0, "sample_ids": []}