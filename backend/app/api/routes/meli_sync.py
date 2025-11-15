from fastapi import APIRouter, HTTPException
from sqlmodel import Session

from app.core.database import engine
from app.core.config import get_settings
from app.repositories.meli_full_sync_job_repo import get_or_create_singleton, reset_queue, save
from app.workers.celery_tasks import meli_full_sync


router = APIRouter()


@router.post("/meli/sync/full-start")
def full_start():
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        if job.status == "running":
            raise HTTPException(status_code=409, detail={"status": "ja_em_execucao"})
        settings = get_settings()
        batch_size = int(getattr(settings, "ML_FULL_SYNC_BATCH", 300))
        job = reset_queue(session, job, batch_size)
    meli_full_sync.delay()
    return {"status": "iniciado"}


@router.get("/meli/sync/status")
def full_status():
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        return {
            "status": job.status,
            "total_previsto": job.total_previsto,
            "processados": job.processados,
            "novos": job.novos,
            "atualizados": job.atualizados,
            "ignorados": job.ignorados,
            "offset_atual": job.offset_atual,
            "batch_tamanho": job.batch_tamanho,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "error_message": job.error_message,
        }


@router.post("/meli/sync/todos-status-start")
def todos_status_start():
    """
    Inicia sincronização completa de TODOS os produtos do Mercado Livre (ativos, vendidos, pausados, encerrados).
    Ideal para inventários grandes (17k+ produtos).
    """
    from app.workers.celery_tasks import meli_full_sync_todos_status
    
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        if job.status == "running":
            raise HTTPException(status_code=409, detail={"status": "ja_em_execucao"})
        # Reset do job para nova sincronização
        settings = get_settings()
        batch_size = 50  # Batch menor para respeitar rate limit
        job = get_or_create_singleton(session)  # Garante singleton
        job.status = "queued"
        job.processados = 0
        job.novos = 0
        job.atualizados = 0
        job.ignorados = 0
        job.offset_atual = 0
        job.batch_tamanho = batch_size
        save(session, job)
    
    meli_full_sync_todos_status.delay()
    return {"status": "iniciado", "tipo": "todos_status"}


@router.post("/meli/sync/incremental-start")
def incremental_start(hours: int = 24):
    """
    Inicia sincronização incremental de produtos modificados nas últimas horas.
    Ideal para atualizações frequentes (ex: a cada 15-30 minutos).
    """
    from app.workers.celery_tasks import meli_incremental_sync
    
    with Session(engine) as session:
        job = get_or_create_singleton(session)
        if job.status == "running":
            raise HTTPException(status_code=409, detail={"status": "ja_em_execucao"})
    
    meli_incremental_sync.delay(hours)
    return {"status": "iniciado", "tipo": "incremental", "hours": hours}