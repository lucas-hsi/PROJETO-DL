from typing import Dict, Optional
import requests

from app.core.config import get_settings
from app.core.logger import logger


def _base_headers() -> Dict[str, str]:
    settings = get_settings()
    return {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base_url() -> str:
    settings = get_settings()
    domain = settings.SHOPIFY_STORE_DOMAIN
    version = settings.SHOPIFY_API_VERSION
    if not domain or not version:
        raise RuntimeError("Shopify domain ou versão não configurados")
    return f"https://{domain}/admin/api/{version}"


def product_exists(sku: str) -> bool:
    """Verifica se já existe variante com SKU no Shopify.
    Estratégia: varrer produtos e variantes (limitado) e conferir SKU.
    """
    url = f"{_base_url()}/products.json?limit=250"
    retries = 3
    wait_seconds = 2
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=_base_headers(), timeout=20)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", wait_seconds))
                time.sleep(retry_after)
                continue
            r.raise_for_status()
            products = r.json().get("products", [])
            for p in products:
                variants = p.get("variants", [])
                for v in variants:
                    if v.get("sku") == sku:
                        return True
            return False
        except requests.RequestException as e:
            logger.error({"event": "shopify_product_exists_error", "error": str(e)})
            time.sleep(wait_seconds)
            continue
    return False


def create_product(product_data: Dict) -> Dict:
    """Cria produto via Admin API.
    Espera product_data com chaves: titulo, descricao, preco, sku.
    """
    payload = {
        "product": {
            "title": product_data.get("titulo"),
            "body_html": product_data.get("descricao"),
            "variants": [
                {
                    "price": str(product_data.get("preco", 0.0)),
                    "sku": product_data.get("sku"),
                    "inventory_management": "shopify",
                }
            ],
        }
    }
    url = f"{_base_url()}/products.json"
    try:
        r = requests.post(url, json=payload, headers=_base_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        logger.info({"event": "shopify_product_created", "product_id": data.get("product", {}).get("id")})
        return data
    except requests.RequestException as e:
        logger.error({"event": "shopify_product_create_error", "error": str(e), "sku": product_data.get("sku")})
        raise


def _get_first_location_id() -> Optional[int]:
    url = f"{_base_url()}/locations.json"
    r = requests.get(url, headers=_base_headers(), timeout=15)
    r.raise_for_status()
    locations = r.json().get("locations", [])
    return locations[0]["id"] if locations else None


def get_product_by_sku(sku: str) -> Optional[Dict]:
    """Retorna o produto Shopify que contém variante com SKU informado."""
    url = f"{_base_url()}/products.json?limit=250"
    r = requests.get(url, headers=_base_headers(), timeout=20)
    r.raise_for_status()
    products = r.json().get("products", [])
    for p in products:
        for v in p.get("variants", []):
            if v.get("sku") == sku:
                return p
    return None


def _get_current_available(inventory_item_id: int, location_id: int) -> int:
    url = f"{_base_url()}/inventory_levels.json?inventory_item_ids={inventory_item_id}&location_ids={location_id}"
    r = requests.get(url, headers=_base_headers(), timeout=15)
    r.raise_for_status()
    levels = r.json().get("inventory_levels", [])
    if not levels:
        return 0
    return int(levels[0].get("available", 0))


def update_inventory(product_id: int, quantity: int) -> Dict:
    """Ajusta nível de estoque para o primeiro local disponível.
    Necessita obter inventory_item_id da primeira variante do produto.
    """
    # Obter produto
    url_prod = f"{_base_url()}/products/{product_id}.json"
    pr = requests.get(url_prod, headers=_base_headers(), timeout=15)
    pr.raise_for_status()
    product = pr.json().get("product", {})
    variants = product.get("variants", [])
    if not variants:
        raise RuntimeError("Produto Shopify sem variantes para ajustar estoque")
    inv_item_id = variants[0].get("inventory_item_id")

    location_id = _get_first_location_id()
    if not location_id:
        raise RuntimeError("Nenhum Location configurado no Shopify")

    # Calcula delta entre desejado e atual
    current = _get_current_available(inv_item_id, location_id)
    delta = int(quantity) - int(current)
    url_adj = f"{_base_url()}/inventory_levels/adjust.json"
    payload = {
        "inventory_item_id": inv_item_id,
        "location_id": location_id,
        "available_adjustment": delta,
    }
    try:
        ar = requests.post(url_adj, json=payload, headers=_base_headers(), timeout=15)
        ar.raise_for_status()
        data = ar.json()
        logger.info({"event": "shopify_inventory_adjusted", "product_id": product_id, "qty": quantity, "delta": delta})
        return data
    except requests.RequestException as e:
        logger.error({"event": "shopify_inventory_adjust_error", "error": str(e), "product_id": product_id})
        raise
