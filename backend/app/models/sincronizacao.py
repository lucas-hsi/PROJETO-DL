from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Sincronizacao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    produto_id: int = Field(index=True)
    origem: str
    destino: str
    acao: str
    status: str
    mensagem: str | None = None
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)