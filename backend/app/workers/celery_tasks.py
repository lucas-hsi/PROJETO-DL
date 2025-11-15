from datetime import timedelta
from sqlmodel import Session

from app.workers.celery_app import celery_app as _celery_app
from app.core.logger import logger
from app.core.database import engine
from app.repositories.produto_repo import list_produtos
from app.services.mercadolivre_service import get_access_token
from app.services.shopify_service import get_product_by_sku, update_inventory
from app.core.config import get_settings
from app.models.meli_full_sync_job import MeliFullSyncJob
from app.repositories.meli_full_sync_job_repo import get_or_create_singleton, save
from app.repositories.produto_repo import save_product
from app.services.mercadolivre_service import meli_request, importar_meli_from_ids
import asyncio
from datetime import datetime
from app.core.database import init_db

# Expor variável esperada pelo CLI (-A app.workers.celery_tasks)
celery = _celery_app


@celery.task(name="ml.refresh_token")
def refresh_ml_token_task():
    try:
        token = get_access_token()
        logger.info({"event": "ml_token_refreshed_task", "preview": token[:6] + "***"})
        return True
    except Exception as e:
        logger.error({"event": "ml_token_refresh_task_error", "error": str(e)})
        return False


@celery.task(name="estoque.sync")
def sync_stock_task():
    synced = 0
    with Session(engine) as session:
        produtos, _ = list_produtos(session, page=1, size=250)
        for p in produtos:
            try:
                sp = get_product_by_sku(p.sku)
                if sp and sp.get("id"):
                    update_inventory(product_id=int(sp.get("id")), quantity=int(p.estoque_atual))
                    synced += 1
            except Exception as e:
                logger.error({"event": "sync_stock_task_error", "sku": p.sku, "error": str(e)})
    logger.info({"event": "sync_stock_task_done", "synced": synced})
    return synced


# Agendamento periódico (necessita executar worker com -B para rodar beat embutido)
celery.conf.beat_schedule = {
    "refresh-ml-token-every-10-min": {
        "task": "ml.refresh_token",
        "schedule": timedelta(minutes=10),
    },
    "sync-stock-every-10-min": {
        "task": "estoque.sync",
        "schedule": timedelta(minutes=10),
    },
    "meli-incremental-sync-every-30-min": {
        "task": "meli.incremental_sync",
        "schedule": timedelta(minutes=30),
        "args": [6],  # Últimas 6 horas
    },
}


@celery.task(name="meli.full_sync")
def meli_full_sync():
    settings = get_settings()
    batch_size = int(getattr(settings, "ML_FULL_SYNC_BATCH", 300))
    max_total = getattr(settings, "ML_FULL_SYNC_MAX", None)
    init_db()
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        if job.status == "running":
            logger.info({"event": "ML_FULL_SYNC_ALREADY_RUNNING"})
            return False
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.error_message = None
        job.batch_tamanho = batch_size
        logger.info({"event": "ML_FULL_SYNC_STARTED"})
        job = save(session, job)
        try:
            seller_id = settings.ML_SELLER_ID
            payload = asyncio.run(meli_request("GET", f"/users/{seller_id}/items/search", params={"status": "active", "limit": 1, "offset": 0}))
            total = int(payload.get("paging", {}).get("total", 0))
            if not job.total_previsto:
                job.total_previsto = total
                job = save(session, job)

            offset = int(job.offset_atual or 0)
            processed = int(job.processados or 0)
            while offset < total:
                if isinstance(max_total, int) and max_total > 0 and processed >= max_total:
                    break
                page = asyncio.run(meli_request("GET", f"/users/{seller_id}/items/search", params={"status": "active", "limit": batch_size, "offset": offset}))
                ids = page.get("results", [])
                if not ids:
                    break
                result = importar_meli_from_ids(ids, dias=None, mode="FULL")
                items = result.get("items", [])
                stats = result.get("stats", {})
                for normalized in items:
                    save_product(session, normalized)
                fetched = int(stats.get("fetched", len(ids)))
                job.processados = processed + fetched
                job.novos += int(stats.get("novos", 0))
                job.atualizados += int(stats.get("atualizados", 0))
                job.ignorados += int(stats.get("ignorados_sem_mudanca", 0))
                job.offset_atual = offset + fetched
                job.batch_tamanho = batch_size
                job = save(session, job)
                offset = job.offset_atual
                processed = job.processados

            job.status = "done"
            job.finished_at = datetime.utcnow()
            save(session, job)
            logger.info({"event": "ML_FULL_SYNC_DONE", "total_previsto": job.total_previsto, "processados": job.processados})
            return True
        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            save(session, job)
            logger.error({"event": "ML_FULL_SYNC_ERROR", "error": str(e)})
            return False


@celery.task(name="meli.full_sync_todos_status")
def meli_full_sync_todos_status():
    """
    Sincronização completa de TODOS os produtos do Mercado Livre (ativos, vendidos, pausados, encerrados).
    Ideal para inventários grandes (17k+ produtos).
    """
    from app.services.mercadolivre_service import importar_meli_todos_status
    
    init_db()
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        if job.status == "running":
            logger.info({"event": "ML_FULL_SYNC_TODOS_STATUS_ALREADY_RUNNING"})
            return False
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.error_message = None
        job.batch_tamanho = 50  # Batch menor para respeitar rate limit
        logger.info({"event": "ML_FULL_SYNC_TODOS_STATUS_STARTED"})
        job = save(session, job)
        
        try:
            # Importa todos os produtos com todos os status
            result = importar_meli_todos_status(limit=50000, dias=None)  # Limite alto para 17k+ produtos
            
            # Salva todos os produtos no banco
            items = result.get("items", [])
            stats = result.get("stats", {})
            
            for normalized in items:
                save_product(session, normalized)
            
            job.status = "done"
            job.finished_at = datetime.utcnow()
            job.processados = stats.get("fetched", 0)
            job.novos = stats.get("novos", 0)
            job.atualizados = stats.get("atualizados", 0)
            job.ignorados = stats.get("ignorados_sem_mudanca", 0)
            job.total_previsto = stats.get("fetched", 0)
            save(session, job)
            
            logger.info({
                "event": "ML_FULL_SYNC_TODOS_STATUS_DONE", 
                "total": stats.get("fetched", 0),
                "novos": stats.get("novos", 0),
                "atualizados": stats.get("atualizados", 0),
                "ignorados": stats.get("ignorados_sem_mudanca", 0)
            })
            return True
            
        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            save(session, job)
            logger.error({"event": "ML_FULL_SYNC_TODOS_STATUS_ERROR", "error": str(e)})
            return False


@celery.task(name="meli.incremental_sync")
def meli_incremental_sync(hours: int = 24):
    """
    Sincronização incremental de produtos do Mercado Livre que foram modificados nas últimas horas.
    Ideal para atualizações frequentes (ex: a cada 15-30 minutos).
    """
    from app.services.mercadolivre_service import importar_meli_incremental
    
    init_db()
    with Session(engine) as session:
        logger.info({"event": "ML_INCREMENTAL_SYNC_STARTED", "hours": hours})
        
        try:
            # Importa apenas produtos modificados recentemente
            result = importar_meli_incremental(hours=hours)
            
            # Salva produtos atualizados no banco
            items = result.get("items", [])
            stats = result.get("stats", {})
            
            for normalized in items:
                save_product(session, normalized)
            
            logger.info({
                "event": "ML_INCREMENTAL_SYNC_DONE", 
                "fetched": stats.get("fetched", 0),
                "novos": stats.get("novos", 0),
                "atualizados": stats.get("atualizados", 0),
                "ignorados": stats.get("ignorados_sem_mudanca", 0),
                "hours": hours
            })
            return True
            
        except Exception as e:
            logger.error({"event": "ML_INCREMENTAL_SYNC_ERROR", "error": str(e), "hours": hours})
            return False