from datetime import timedelta
from sqlmodel import Session

from app.workers.celery_app import celery_app as _celery_app
from app.core.logger import logger
from app.core.database import engine
from app.repositories.produto_repo import list_produtos
from app.services.mercadolivre_service import get_access_token
from app.services.shopify_service import get_product_by_sku, update_inventory

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
}