from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class Usuario(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email", name="uq_usuario_email"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    senha_hash: str
    role: str
    is_active: bool = True
