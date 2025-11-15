from typing import Optional
from datetime import datetime

from sqlmodel import Session, select

from app.models.meli_full_sync_job import MeliFullSyncJob


def get_or_create_singleton(session: Session) -> MeliFullSyncJob:
    job = session.exec(select(MeliFullSyncJob).order_by(MeliFullSyncJob.id.asc()).limit(1)).first()
    if job:
        return job
    job = MeliFullSyncJob(id=1, status="idle")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def save(session: Session, job: MeliFullSyncJob) -> MeliFullSyncJob:
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def reset_queue(session: Session, job: MeliFullSyncJob, batch_size: int) -> MeliFullSyncJob:
    job.status = "queued"
    job.processados = 0
    job.novos = 0
    job.atualizados = 0
    job.ignorados = 0
    job.offset_atual = 0
    job.batch_tamanho = batch_size
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    return save(session, job)