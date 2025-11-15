from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from sqlalchemy import asc, desc, func

from app.core.database import get_session
from app.schemas.produto import ProdutoCreate, ProdutoRead
from app.repositories.produto_repo import (
    create_produto,
    list_produtos,
    save_product,
    get_by_sku,
)
from app.services.mercadolivre_service import (
    get_meli_products,
    normalize_meli_product,
    importar_meli,
    importar_meli_todos_status,
    importar_meli_incremental,
)
from app.services.mercadolivre_service import MeliAuthError
from app.models.ml_log import MLLog
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
    origem: str | None = Query(None),
):
    if origem:
        from app.models.produto import Produto
        sort_col = getattr(Produto, sort_by, Produto.created_at)
        order = desc(sort_col) if sort_dir.lower() == "desc" else asc(sort_col)
        total = session.exec(select(func.count()).select_from(Produto).where(Produto.origem == origem)).one()
        query = select(Produto).where(Produto.origem == origem).order_by(order).offset((page - 1) * size).limit(size)
        items = session.exec(query).all()
    else:
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
def importar_meli_endpoint(
    limit: int = Query(100, ge=1, le=500),
    dias: int | None = Query(None, ge=1, le=30),
    novos: bool = Query(False),
    session: Session = Depends(get_session),
):
    try:
        logger.info({"event": "IMPORT_MELI_START", "limit": limit, "dias": dias, "novos": novos})
        result = importar_meli(limit=limit, dias=dias, novos=novos)
        count = 0
        for normalized in result.get("items", []):
            save_product(session, normalized)
            count += 1
        tempo_exec = result.get("tempo_execucao")
        logger.info({"event": "IMPORT_MELI_DONE", "importados": count, "duracao": tempo_exec})
        return {
            "status": "sucesso",
            "importados": count,
            "limite": limit,
            "origem": "Mercado Livre",
            "tempo_execucao": tempo_exec,
        }
    except MeliAuthError as auth_e:
        logger.error({"event": "IMPORT_MELI_FAIL", "status": auth_e.status, "endpoint": auth_e.endpoint})
        http_status = 401 if auth_e.status == 401 else 502
        detail = {
            "status": "erro",
            "tipo": "ML_AUTH",
            "http_status": auth_e.status,
            "endpoint": auth_e.endpoint,
            "detalhe": auth_e.body,
        }
        raise HTTPException(status_code=http_status, detail=detail)
    except Exception as e:
        logger.error({"event": "IMPORT_MELI_FAIL", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha ao importar do Mercado Livre")


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
                    update_inventory(prod_id, int(float(p.estoque_atual or 0)))
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


@router.get("/meli/status")
def meli_status(session: Session = Depends(get_session)):
    try:
        from sqlmodel import select
        last = session.exec(select(MLLog).order_by(MLLog.created_at.desc()).limit(1)).first()
        if not last:
            return {"status": "vazio"}
        return {
            "status": last.status,
            "origem": last.origem,
            "total_importado": last.total_importado,
            "duracao_segundos": last.duracao_segundos,
            "created_at": last.created_at.isoformat(),
        }
    except Exception as e:
        logger.error({"event": "meli_status_error", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha ao consultar status")


@router.post("/importar-meli-todos-status")
def importar_meli_todos_status_endpoint(
    limit: int = Query(20000, ge=1, le=50000),
    dias: int | None = Query(None, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """
    Importa TODOS os produtos do Mercado Livre (ativos, vendidos, pausados, encerrados).
    Ideal para sincronização completa de grandes inventários (17k+ produtos).
    """
    try:
        logger.info({"event": "IMPORT_MELI_TODOS_STATUS_START", "limit": limit, "dias": dias})
        result = importar_meli_todos_status(limit=limit, dias=dias)
        count = 0
        for normalized in result.get("items", []):
            save_product(session, normalized)
            count += 1
        tempo_exec = result.get("tempo_execucao")
        logger.info({"event": "IMPORT_MELI_TODOS_STATUS_DONE", "importados": count, "duracao": tempo_exec})
        return {
            "status": "sucesso",
            "importados": count,
            "limite": limit,
            "origem": "Mercado Livre - Todos Status",
            "tempo_execucao": tempo_exec,
            "stats": {
                "fetched": result.get("fetched", 0),
                "novos": result.get("novos", 0),
                "atualizados": result.get("atualizados", 0),
                "ignorados": result.get("ignorados_sem_mudanca", 0)
            }
        }
    except MeliAuthError as auth_e:
        logger.error({"event": "IMPORT_MELI_TODOS_STATUS_FAIL", "status": auth_e.status, "endpoint": auth_e.endpoint})
        http_status = 401 if auth_e.status == 401 else 502
        detail = {
            "status": "erro",
            "tipo": "ML_AUTH",
            "http_status": auth_e.status,
            "endpoint": auth_e.endpoint,
            "detalhe": auth_e.body,
        }
        raise HTTPException(status_code=http_status, detail=detail)
    except Exception as e:
        logger.error({"event": "IMPORT_MELI_TODOS_STATUS_FAIL", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha ao importar todos os produtos do Mercado Livre")


@router.post("/importar-meli-incremental")
def importar_meli_incremental_endpoint(
    hours: int = Query(24, ge=1, le=168),
    session: Session = Depends(get_session),
):
    """
    Importa apenas produtos que foram modificados nas últimas horas.
    Ideal para sincronização incremental frequente (ex: a cada 15-30 minutos).
    """
    try:
        logger.info({"event": "IMPORT_MELI_INCREMENTAL_START", "hours": hours})
        result = importar_meli_incremental(hours=hours)
        count = 0
        for normalized in result.get("items", []):
            save_product(session, normalized)
            count += 1
        tempo_exec = result.get("tempo_execucao")
        logger.info({"event": "IMPORT_MELI_INCREMENTAL_DONE", "importados": count, "duracao": tempo_exec})
        return {
            "status": "sucesso",
            "importados": count,
            "horas": hours,
            "origem": "Mercado Livre - Incremental",
            "tempo_execucao": tempo_exec,
            "stats": {
                "fetched": result.get("fetched", 0),
                "novos": result.get("novos", 0),
                "atualizados": result.get("atualizados", 0),
                "ignorados": result.get("ignorados_sem_mudanca", 0)
            }
        }
    except MeliAuthError as auth_e:
        logger.error({"event": "IMPORT_MELI_INCREMENTAL_FAIL", "status": auth_e.status, "endpoint": auth_e.endpoint})
        http_status = 401 if auth_e.status == 401 else 502
        detail = {
            "status": "erro",
            "tipo": "ML_AUTH",
            "http_status": auth_e.status,
            "endpoint": auth_e.endpoint,
            "detalhe": auth_e.body,
        }
        raise HTTPException(status_code=http_status, detail=detail)
    except Exception as e:
        logger.error({"event": "IMPORT_MELI_INCREMENTAL_FAIL", "error": str(e)})
        raise HTTPException(status_code=500, detail="Falha ao importar produtos incrementais do Mercado Livre")
