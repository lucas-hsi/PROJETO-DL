import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from app.core.config import get_settings
from app.core.logger import logger


def get_access_token() -> str:
    settings = get_settings()
    if getattr(settings, "ML_ACCESS_TOKEN", ""):
        logger.info({
            "event": "ML_ACCESS_TOKEN_USED",
            "status": "sucesso",
            "timestamp": datetime.utcnow().isoformat()
        })
        return settings.ML_ACCESS_TOKEN

    new_access, _ = refresh_access_token()
    if not new_access:
        raise RuntimeError("Falha ao renovar token do Mercado Livre")
    return new_access


def refresh_access_token() -> tuple[str | None, str | None]:
    settings = get_settings()
    url = f"{settings.ML_API_BASE_URL}/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.ML_CLIENT_ID,
        "client_secret": settings.ML_CLIENT_SECRET,
        "refresh_token": settings.ML_REFRESH_TOKEN,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = requests.post(url, data=payload, headers=headers, timeout=15)
        status_code = resp.status_code
        body = {}
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        if status_code >= 400:
            logger.error({
                "event": "ML_TOKEN_REFRESH_FAIL",
                "status": status_code,
                "url": url,
                "body": body,
            })
            return None, None
        data = body
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        masked = dict(data)
        if "access_token" in masked and isinstance(masked["access_token"], str):
            masked["access_token"] = masked["access_token"][:6] + "***"
        if "refresh_token" in masked and isinstance(masked["refresh_token"], str):
            masked["refresh_token"] = masked["refresh_token"][:6] + "***"
        if new_access:
            logger.info({
                "event": "ML_TOKEN_REFRESH_OK",
                "status": status_code,
                "url": url,
                "body": masked,
            })
            return new_access, new_refresh
        logger.warning({"event": "ML_TOKEN_REFRESH_NO_DATA", "status": status_code, "body": masked})
        return None, None
    except requests.exceptions.RequestException as e:
        logger.error({
            "event": "ML_TOKEN_REFRESH_FAIL",
            "error": str(e),
            "response": getattr(e.response, "text", None),
            "url": url,
        })
        return None, None


def _auth_params(token: str) -> Dict[str, str]:
    return {"access_token": token}


def get_meli_products(limit: Optional[int] = None) -> List[Dict]:
    """
    Importa produtos do Mercado Livre com limite configurável e controle de taxa.
    Respeita 429 (Retry-After) e limita a 100 por execução (configurável).
    """
    settings = get_settings()
    token = get_access_token()
    seller_id = settings.ML_SELLER_ID
    headers = {"Authorization": f"Bearer {token}"}

    max_limit = int(limit or getattr(settings, "ML_IMPORT_LIMIT", 100))
    batch_size = 50  # limite típico por requisição
    all_items: List[str] = []
    offset = 0

    # Paginação de IDs
    while len(all_items) < max_limit:
        url = f"{settings.ML_API_BASE_URL}/users/{seller_id}/items/search"
        params = {"limit": batch_size, "offset": offset}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code == 429:
                retry = int(r.headers.get("Retry-After", 2))
                logger.info({"event": "ml_rate_limit", "stage": "list", "sleep": retry})
                time.sleep(retry)
                continue
            r.raise_for_status()
            data = r.json()
            ids = data.get("results", [])
            if not ids:
                break
            all_items.extend(ids)
            offset += batch_size
            # Segurança anti-bloqueio
            time.sleep(0.3)
            if len(all_items) >= max_limit:
                all_items = all_items[:max_limit]
                break
        except requests.RequestException as e:
            logger.error({"event": "ml_list_items_error", "error": str(e)})
            break

    # Busca detalhes de cada item com controle de taxa
    detailed: List[Dict] = []
    for item_id in all_items:
        item_url = f"{settings.ML_API_BASE_URL}/items/{item_id}"
        try:
            ir = requests.get(item_url, headers=headers, timeout=15)
            if ir.status_code == 429:
                retry = int(ir.headers.get("Retry-After", 3))
                logger.info({"event": "ml_rate_limit", "stage": "item", "sleep": retry, "item_id": item_id})
                time.sleep(retry)
                continue
            ir.raise_for_status()
            detailed.append(ir.json())
            time.sleep(0.25)
        except requests.RequestException as e:
            logger.error({"event": "ml_item_fetch_error", "item_id": item_id, "error": str(e)})
            continue
    return detailed


def normalize_meli_product(item: Dict) -> Dict:
    """Converte formato ML para padrão interno (Produto)."""
    return {
        "sku": str(item.get("id")),
        "titulo": item.get("title") or "Produto ML",
        "descricao": item.get("permalink"),
        "preco": float(item.get("price") or 0.0),
        "estoque_atual": int(item.get("available_quantity") or 0),
        "origem": "MERCADO_LIVRE",
        "status": "ATIVO",
    }

if __name__ == "__main__":
    print(refresh_access_token())