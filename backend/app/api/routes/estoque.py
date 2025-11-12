from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.produto import ProdutoCreate, ProdutoRead
from app.repositories.produto_repo import (
    create_produto,
    list_produtos,
    save_product,
    get_by_sku,
)
from app.services.mercadolivre_service import get_meli_products, normalize_meli_product
from app.services.shopify_service import product_exists, create_product, update_inventory, get_product_by_sku
from app.core.logger import logger
from app.core.config import get_settings
from time import perf_counter

router = APIRouter(prefix="/estoque")


@router.get("")
def get_estoque(
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
):
    items, total = list_produtos(session, page=page, size=size, sort_by=sort_by, sort_dir=sort_dir)
    return {
        "items": [ProdutoRead.model_validate(i).model_dump() for i in items],
        "page": page,
        "size": size,
        "total": total,
    }


@router.post("")
def post_estoque(data: ProdutoCreate, session: Session = Depends(get_session)):
    try:
        produto = create_produto(session, data)
        return ProdutoRead.model_validate(produto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/importar-meli")
def importar_meli(session: Session = Depends(get_session)):
    try:
        settings = get_settings()
        limit = int(getattr(settings, "ML_IMPORT_LIMIT", 100))
        start = perf_counter()
        items = get_meli_products(limit=limit)
        count = 0
        for it in items:
            normalized = normalize_meli_product(it)
            save_product(session, normalized)
            count += 1
        tempo_exec = round(perf_counter() - start, 2)
        logger.info({"event": "IMPORT_MELI", "importados": count, "limite": limit, "tempo_exec": tempo_exec})
        logger.info(f"[IMPORT_MELI] Importados {count} itens em {tempo_exec}s.")
        return {
            "status": "sucesso",
            "importados": count,
            "limite": limit,
            "origem": "Mercado Livre",
            "tempo_execucao": f"{tempo_exec}s",
        }
    except Exception as e:
        logger.error({"event": "IMPORT_MELI_ERROR", "error": str(e)})
        logger.error(f"[IMPORT_MELI_ERROR] {str(e)}")
        return {"detail": "Falha ao importar do Mercado Livre"}


@router.post("/publicar-shopify")
def publicar_shopify(session: Session = Depends(get_session)):
    try:
        # Carrega página de produtos; publica todos que não existirem no Shopify
        produtos, _ = list_produtos(session, page=1, size=250)
        publicados = 0
        for p in produtos:
            if product_exists(p.sku):
                continue
            # Cria produto
            payload = {
                "titulo": p.titulo,
                "descricao": p.descricao,
                "preco": p.preco,
                "sku": p.sku,
            }
            data = create_product(payload)
            prod_id = data.get("product", {}).get("id")
            if prod_id:
                # Ajusta estoque para refletir estoque_atual
                try:
                    update_inventory(prod_id, int(p.estoque_atual))
                except Exception as inv_e:
                    logger.error({"event": "shopify_inventory_adjust_error", "error": str(inv_e), "sku": p.sku})
                publicados += 1
        logger.info({"event": "shopify_publish_done", "count": publicados})
        return {"status": "sucesso", "publicados": publicados, "destino": "Shopify"}
    except Exception as e:
        logger.error({"event": "shopify_publish_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha ao publicar no Shopify")


@router.get("/sincronizar")
def sincronizar(session: Session = Depends(get_session)):
    try:
        # Retorna lista de itens normalizados para o frontend
        produtos, _ = list_produtos(session, page=1, size=250)
        itens = []
        for p in produtos:
            try:
                itens.append({
                    "sku": p.sku,
                    "titulo": p.titulo,
                    "preco": float(p.preco or 0.0),
                    "estoque": int(p.estoque_atual or 0),
                    "origem": p.origem,
                    "data_importacao": getattr(p, "updated_at", None).isoformat() if getattr(p, "updated_at", None) else None,
                })
            except Exception as inner:
                logger.error({"event": "sync_item_format_error", "sku": p.sku, "error": str(inner)})
                continue
        return {"status": "ok", "itens": itens}
    except Exception as e:
        logger.error({"event": "sync_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha na sincronização")