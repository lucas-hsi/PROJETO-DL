import os
import pytest
import requests

from app.core.config import get_settings


DOMAIN = os.getenv("TEST_DOMAIN_URL", "https://app.dlautopecas.com.br")
API_HEALTH_URL = f"{DOMAIN}/api/health"


def _domain_available() -> bool:
    try:
        r = requests.get(API_HEALTH_URL, timeout=3)
        return r.status_code < 500
    except Exception:
        return False


@pytest.mark.skipif(not _domain_available(), reason="Domínio indisponível para teste externo")
def test_domain_health_ok():
    r = requests.get(API_HEALTH_URL, timeout=5)
    assert r.status_code == 200


@pytest.mark.skipif(not _domain_available(), reason="Domínio indisponível para teste externo")
def test_http_redirects_to_https():
    http_domain = DOMAIN.replace("https://", "http://")
    # usar allow_redirects=False para verificar código de redirecionamento
    r = requests.get(http_domain, timeout=5, allow_redirects=False)
    assert r.status_code in (301, 302, 308)


def test_env_variables_loaded():
    settings = get_settings()
    # ML_REDIRECT_URI deve ser carregada via env sem fallback hardcoded
    redirect = getattr(settings, "ML_REDIRECT_URI", "")
    assert isinstance(redirect, str)
    # quando configurado, deve apontar para o domínio oficial
    if redirect:
        assert redirect.endswith("/auth/meli/callback")