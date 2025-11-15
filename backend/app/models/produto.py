from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Column
from sqlalchemy.dialects.postgresql import JSONB


class Produto(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("sku", name="uq_produto_sku"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(index=True)
    titulo: str
    descricao: Optional[str] = None
    preco: float = 0.0
    estoque_atual: int = 0
    origem: str = "LOCAL"
    status: str = "ATIVO"
    imagens: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
