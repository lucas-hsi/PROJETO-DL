import os
import json
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
import requests

from app.core.logger import logger
from app.core.config import get_settings


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

        try:
            settings = get_settings()
            if access_token:
                setattr(settings, "ML_ACCESS_TOKEN", access_token)
            if refresh_token:
                setattr(settings, "ML_REFRESH_TOKEN", refresh_token)
            expires_in = data.get("expires_in")
            settings.APP_VERSION = settings.APP_VERSION  # touch to avoid lint
            try:
                from fastapi import FastAPI
            except Exception:
                pass
            _persist_tokens_to_env(access_token, refresh_token)
            logger.info({"event": "ML_TOKEN_EXCHANGE_OK", "status": status_code})
        except Exception as e:
            logger.error({"event": "ML_TOKEN_UPDATE_FAIL", "error": str(e)})

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
    settings = get_settings()
    raw_access = getattr(settings, "ML_ACCESS_TOKEN", "")
    raw_refresh = getattr(settings, "ML_REFRESH_TOKEN", "")
    def _mask(v: str) -> str:
        return v[:6] + "***" if isinstance(v, str) and v else None
    return {
        "raw_access_token": _mask(raw_access),
        "raw_refresh_token": _mask(raw_refresh),
        "expires_in": None,
        "seller_id": getattr(settings, "ML_SELLER_ID", None),
        "env_loaded": True,
    }


def _persist_tokens_to_env(access_token: str | None, refresh_token: str | None) -> None:
    try:
        env_path = os.path.join(os.getcwd(), ".env")
        env_path = os.path.normpath(env_path)
        lines: list[str] = []
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            lines = []
        def upsert_line(key: str, value: str | None):
            if value is None:
                return
            found = False
            for i, ln in enumerate(lines):
                if ln.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={value}")
        upsert_line("ML_ACCESS_TOKEN", access_token)
        upsert_line("ML_REFRESH_TOKEN", refresh_token)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        logger.error({"event": "ML_ENV_PERSIST_FAIL", "error": str(e)})