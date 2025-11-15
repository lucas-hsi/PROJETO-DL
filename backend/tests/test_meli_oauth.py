from fastapi.testclient import TestClient
import os
import pytest

from app.main import app
from app.core.config import get_settings
from app.services.mercadolivre_service import get_access_token, refresh_access_token, MeliAuthError


client = TestClient(app)


def _has_ml_credentials():
    s = get_settings()
    return bool(s.ML_CLIENT_ID and s.ML_CLIENT_SECRET and s.ML_REDIRECT_URI)


def test_meli_authorize_redirect_url():
    if not _has_ml_credentials():
        pytest.skip("Credenciais ML ausentes")
    s = get_settings()
    assert s.ML_REDIRECT_URI == "https://dlautopecas.com.br/auth/meli/callback"
    r = client.get("/meli/authorize", allow_redirects=False)
    assert r.status_code in (302, 307)
    location = r.headers.get("location", "")
    assert location.startswith("https://auth.mercadolivre.com.br/authorization?response_type=code")
    assert f"client_id={s.ML_CLIENT_ID}" in location
    assert f"redirect_uri={s.ML_REDIRECT_URI}" in location


def test_debug_token_masks_values():
    r = client.get("/meli/debug-token")
    assert r.status_code == 200
    data = r.json()
    ra = data.get("raw_access_token")
    rr = data.get("raw_refresh_token")
    if ra:
        assert ra.endswith("***")
    if rr:
        assert rr.endswith("***")


def test_get_access_token_returns_valid_or_raises():
    if not _has_ml_credentials():
        pytest.skip("Credenciais ML ausentes")
    try:
        token = get_access_token()
        assert isinstance(token, str)
        assert not token.startswith("TG-")
    except MeliAuthError as e:
        assert e.status in (400, 401)


def test_refresh_access_token_flow():
    if not _has_ml_credentials():
        pytest.skip("Credenciais ML ausentes")
    s = get_settings()
    if not s.ML_REFRESH_TOKEN:
        pytest.skip("Sem refresh token configurado")
    try:
        access, refresh = refresh_access_token()
        assert isinstance(access, str)
    except MeliAuthError as e:
        assert e.status in (400, 401)


def test_importar_meli_endpoint():
    if not _has_ml_credentials():
        pytest.skip("Credenciais ML ausentes")
    r = client.post("/estoque/importar-meli", params={"limit": 10})
    assert r.status_code in (200, 401, 502)
    if r.status_code == 200:
        body = r.json()
        assert body.get("status") == "sucesso"