from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Optional, List


class ProdutoCreate(BaseModel):
    sku: str
    titulo: str
    descricao: Optional[str] = None
    preco: float = Field(ge=0)
    estoque_atual: int = Field(ge=0)
    origem: str = "LOCAL"
    status: str = "ATIVO"


class ProdutoRead(BaseModel):
    id: int
    sku: str
    titulo: str
    descricao: Optional[str] = None
    preco: float
    estoque_atual: int
    origem: str
    status: str
    imagens: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    # Permite validar a partir de objetos ORM (SQLModel) em Pydantic v2
    model_config = ConfigDict(from_attributes=True)