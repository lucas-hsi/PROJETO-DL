import os
import json
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
import requests

from app.core.logger import logger
from app.core.config import get_settings
from app.services.mercadolivre_service import save_tokens_to_db


router = APIRouter()

def _get_meli_env():
    settings = get_settings()
    return {
        "client_id": getattr(settings, "ML_CLIENT_ID", os.getenv("ML_CLIENT_ID", "")),
        "client_secret": getattr(settings, "ML_CLIENT_SECRET", os.getenv("ML_CLIENT_SECRET", "")),
        "redirect_uri": getattr(settings, "ML_REDIRECT_URI", os.getenv("ML_REDIRECT_URI", "")),
        "api_base": getattr(settings, "ML_API_BASE_URL", os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com")),
    }


@router.get("/meli/authorize")
def meli_authorize():
    env = _get_meli_env()
    url = (
        "https://auth.mercadolivre.com.br/authorization?response_type=code"
        f"&client_id={env['client_id']}&redirect_uri={env['redirect_uri']}"
    )
    logger.info({"event": "ML_AUTHORIZE_START", "auth_url": url})
    return RedirectResponse(url)


@router.get("/auth/meli/callback", response_class=HTMLResponse)
def meli_callback(code: str = Query(...)):
    env = _get_meli_env()
    token_url = f"{env['api_base']}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": env["client_id"],
        "client_secret": env["client_secret"],
        "code": code,
        "redirect_uri": env["redirect_uri"],
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
        expires_in = data.get("expires_in")
        token_type = data.get("token_type")
        scope = data.get("scope")
        user_id = data.get("user_id")

        try:
            save_tokens_to_db(access_token, refresh_token, expires_in, token_type, scope, user_id)
            logger.info({"event": "ML_TOKEN_EXCHANGE_OK", "status": status_code})
        except Exception as e:
            logger.error({"event": "ML_TOKEN_SAVE_DB_FAIL", "error": str(e)})

        html = (
            "<html><body style='font-family:Arial;text-align:center;padding:50px'>"
            "<h2>✅ Conexão realizada com sucesso!</h2>"
            "<p>Feche esta aba e volte ao sistema.</p>"
            f"<p><b>Status:</b> {status_code}</p>"
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

# Redirect URI oficial do ambiente: app.dlautopecas.com.br/auth/meli/callback


@router.get("/meli/debug-token")
def meli_debug_token():
    try:
        from sqlmodel import Session, select
        from app.core.database import engine
        from app.models.ml_token import MlToken
        with Session(engine) as s:
            row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
        def _mask(v: str) -> str:
            return v[:6] + "***" if isinstance(v, str) and v else None
        return {
            "raw_access_token": _mask(getattr(row, "access_token", None) or ""),
            "raw_refresh_token": _mask(getattr(row, "refresh_token", None) or ""),
            "expires_in": getattr(row, "expires_in", None),
            "seller_id": getattr(row, "user_id", None),
            "env_loaded": False,
        }
    except Exception as e:
        return {"error": str(e)}


def _persist_tokens_to_env(access_token: str | None, refresh_token: str | None) -> None:
    return None