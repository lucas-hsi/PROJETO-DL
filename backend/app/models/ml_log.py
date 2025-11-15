from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class MLLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    origem: str = "MERCADO_LIVRE"
    total_importado: int = 0
    duracao_segundos: float = 0.0
    status: str = "sucesso"
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
