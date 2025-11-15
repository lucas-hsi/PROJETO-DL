from datetime import datetime
from typing import Optional, Any

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Column
from sqlalchemy.dialects.postgresql import JSONB


class MeliItemSnapshot(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("sku", "meli_id", name="uq_meli_item_snapshot_sku_meli_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(index=True)
    meli_id: str = Field(index=True)
    hash_conteudo: str
    status_meli: str
    primeira_importacao_em: datetime = Field(default_factory=datetime.utcnow, index=True)
    ultima_sincronizacao_em: datetime = Field(default_factory=datetime.utcnow, index=True)
    ultima_modificacao_detectada_em: Optional[datetime] = Field(default=None, index=True)
    raw_payload: Optional[Any] = Field(default=None, sa_column=Column(JSONB))