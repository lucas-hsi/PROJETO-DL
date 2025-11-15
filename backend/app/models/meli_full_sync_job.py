from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class MeliFullSyncJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="idle")
    total_previsto: Optional[int] = None
    processados: int = 0
    novos: int = 0
    atualizados: int = 0
    ignorados: int = 0
    offset_atual: int = 0
    batch_tamanho: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None