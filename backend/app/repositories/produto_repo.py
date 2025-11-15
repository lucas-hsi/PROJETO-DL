from typing import List, Tuple, Optional
from sqlmodel import Session, select
from sqlalchemy import asc, desc, func

from app.models.produto import Produto
from app.schemas.produto import ProdutoCreate
from app.core.logger import logger


def create_produto(session: Session, data: ProdutoCreate) -> Produto:
    # Verificar SKU único
    exists = session.exec(select(Produto).where(Produto.sku == data.sku)).first()
    if exists:
        raise ValueError("SKU já existente")

    produto = Produto(
        sku=data.sku,
        titulo=data.titulo,
        descricao=data.descricao,
        preco=data.preco,
        estoque_atual=data.estoque_atual,
        origem=data.origem,
        status=data.status,
    )
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


def get_by_sku(session: Session, sku: str) -> Optional[Produto]:
    return session.exec(select(Produto).where(Produto.sku == sku)).first()


def save_product(session: Session, data: dict) -> Produto:
    """Idempotente: cria ou atualiza produto pelo SKU."""
    sku = data.get("sku")
    produto = get_by_sku(session, sku)
    if produto:
        produto.titulo = data.get("titulo", produto.titulo)
        produto.descricao = data.get("descricao", produto.descricao)
        produto.preco = float(data.get("preco", produto.preco or 0.0))
        produto.estoque_atual = int(data.get("estoque_atual", produto.estoque_atual or 0))
        produto.origem = data.get("origem", produto.origem)
        produto.status = data.get("status", produto.status)
        imagens = data.get("imagens")
        if imagens is not None:
            produto.imagens = imagens
        session.add(produto)
        session.commit()
        session.refresh(produto)
        logger.info({"event": "produto_salvo_update", "sku": sku})
        return produto
    # Criar novo
    novo = Produto(
        sku=data.get("sku"),
        titulo=data.get("titulo"),
        descricao=data.get("descricao"),
        preco=float(data.get("preco", 0.0)),
        estoque_atual=int(data.get("estoque_atual", 0)),
        origem=data.get("origem", "LOCAL"),
        status=data.get("status", "ATIVO"),
        imagens=data.get("imagens") or [],
    )
    session.add(novo)
    session.commit()
    session.refresh(novo)
    logger.info({"event": "produto_salvo_create", "sku": novo.sku})
    return novo


def update_stock(session: Session, sku: str, quantity: int) -> Produto:
    produto = get_by_sku(session, sku)
    if not produto:
        raise ValueError("Produto não encontrado para atualizar estoque")
    produto.estoque_atual = int(quantity)
    session.add(produto)
    session.commit()
    session.refresh(produto)
    return produto


def list_produtos(
    session: Session,
    page: int = 1,
    size: int = 10,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> Tuple[List[Produto], int]:
    # Campo de ordenação dinâmico
    sort_col = getattr(Produto, sort_by, Produto.created_at)
    order = desc(sort_col) if sort_dir.lower() == "desc" else asc(sort_col)

    total = session.exec(select(func.count()).select_from(Produto)).one()
    query = select(Produto).order_by(order).offset((page - 1) * size).limit(size)
    items = session.exec(query).all()
    return items, total
