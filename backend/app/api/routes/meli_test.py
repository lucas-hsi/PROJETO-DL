from fastapi import APIRouter
from app.services.mercadolivre_service import meli_request, MeliAuthError, importar_meli_async
from app.core.logger import logger
from app.core.config import get_settings

router = APIRouter()


@router.get("/meli/full-test")
async def meli_full_test():
    settings = get_settings()
    try:
        who = await meli_request("GET", "/users/me")
        who_status = 200
    except MeliAuthError as e:
        who = {}
        who_status = e.status

    try:
        sample = await meli_request("GET", f"/users/{settings.ML_SELLER_ID}/items/search", params={"status": "active", "limit": 5})
        sample_status = 200
        sample_ids = sample.get("results", [])[:5]
    except MeliAuthError as e:
        sample_status = e.status
        sample_ids = []

    items, count = await importar_meli_async(limit=2)
    import_status = "OK"

    result = {
        "whoami_status": who_status,
        "sample_status": sample_status,
        "sample_ids": sample_ids,
        "import_status": import_status,
        "importados": count,
    }
    logger.info({"event": "ML_FULL_TEST", "result": result})
    return result