from typing import List
import requests
from sqlmodel import Session, select

from app.core.logger import logger
from app.core.config import get_settings
from app.models.produto import Produto


def fetch_mercadolivre_products(query: str = "auto pecas", limit: int = 10) -> List[dict]:
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": query, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    return results


def seed_from_mercadolivre(session: Session, limit: int = 5):
    logger.info({"event": "seed_start", "source": "mercadolivre", "limit": limit})
    items = fetch_mercadolivre_products(limit=limit)
    count = 0
    for it in items:
        sku = str(it.get("id"))
        titulo = it.get("title") or "Produto Mercado Livre"
        preco = float(it.get("price") or 0.0)
        estoque = int(it.get("available_quantity") or 0)

        # Verifica existência por SKU
        exists = session.exec(select(Produto).where(Produto.sku == sku)).first()
        if exists:
            continue

        produto = Produto(
            sku=sku,
            titulo=titulo,
            descricao=it.get("permalink"),
            preco=preco,
            estoque_atual=estoque,
            origem="MERCADO_LIVRE",
            status="ATIVO",
        )
        session.add(produto)
        count += 1

    session.commit()
    logger.info({"event": "seed_done", "inserted": count})