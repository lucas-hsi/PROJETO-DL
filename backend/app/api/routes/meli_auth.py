import os
import json
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, HTMLResponse
import requests

from app.core.logger import logger


router = APIRouter()

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
ML_API_BASE_URL = os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com")


@router.get("/meli/authorize")
def meli_authorize():
    url = (
        "https://auth.mercadolibre.com/authorization?response_type=code"
        f"&client_id={ML_CLIENT_ID}&redirect_uri={ML_REDIRECT_URI}"
    )
    logger.info({"event": "ML_AUTH_URL_GENERATED", "auth_url": url})
    return {"auth_url": url}


@router.get("/auth/meli/callback", response_class=HTMLResponse)
def meli_callback(code: str = Query(...)):
    token_url = f"{ML_API_BASE_URL}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        resp = requests.post(token_url, data=payload, headers=headers, timeout=15)
        status_code = resp.status_code
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        log_payload = dict(data)
        if isinstance(log_payload.get("access_token"), str):
            log_payload["access_token"] = log_payload["access_token"][:6] + "***"
        if isinstance(log_payload.get("refresh_token"), str):
            log_payload["refresh_token"] = log_payload["refresh_token"][:6] + "***"
        logger.info({"event": "ML_CODE_EXCHANGE", "status": status_code, "body": log_payload})

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if access_token:
            print("\n[ML_AUTH] access_token=", access_token)
        if refresh_token:
            print("[ML_AUTH] refresh_token=", refresh_token)

        html = (
            "<html><body style='font-family:Arial;text-align:center;padding:50px'>"
            "<h2>✅ Autorização Mercado Livre concluída!</h2>"
            f"<p><b>Status:</b> {status_code}</p>"
            f"<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"
            "<p>Copie os tokens acima e salve no .env.</p>"
            "</body></html>"
        )
        return html
    except requests.exceptions.RequestException as e:
        logger.error({
            "event": "ML_CODE_EXCHANGE_FAIL",
            "error": str(e),
            "response": getattr(e.response, "text", None),
            "url": token_url,
        })
        return JSONResponse({"error": str(e)}, status_code=500)