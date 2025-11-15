from sqlmodel import Session, select
from time import sleep

from app.core.database import engine, init_db
from app.models.meli_item_snapshot import MeliItemSnapshot
from app.services.meli_hash_utils import compute_meli_item_hash
from app.repositories.meli_item_snapshot_repo import (
    upsert_snapshot_new,
    get_snapshot_by_sku,
    mark_snapshot_unchanged,
    update_snapshot_changed,
)


def test_snapshot_lifecycle():
    init_db()
    with Session(engine) as session:
        sku = "TEST-SKU-123"
        raw = {"id": sku, "title": "Item X", "price": 100.0, "status": "active"}
        normalized = {
            "sku": sku,
            "titulo": "Item X",
            "descricao": "http://example",
            "preco": 100.0,
            "estoque_atual": 1,
            "origem": "MERCADO_LIVRE",
            "status": "ATIVO",
            "imagens": ["http://img1", "http://img2"],
        }
        # Novo
        h1 = compute_meli_item_hash(normalized, raw)
        snap = upsert_snapshot_new(session, sku, raw["id"], h1, raw["status"], {"id": raw["id"], "title": raw["title"], "price": raw["price"], "status": raw["status"]})
        assert snap.sku == sku
        assert snap.hash_conteudo == h1

        # Unchanged
        sleep(0.5)
        snap2 = get_snapshot_by_sku(session, sku)
        before_mod = snap2.ultima_modificacao_detectada_em
        snap2 = mark_snapshot_unchanged(session, snap2)
        assert snap2.ultima_modificacao_detectada_em == before_mod

        # Changed
        normalized_changed = dict(normalized)
        normalized_changed["preco"] = 110.0
        h2 = compute_meli_item_hash(normalized_changed, raw)
        snap3 = update_snapshot_changed(session, snap2, h2, raw["status"], {"id": raw["id"], "title": raw["title"], "price": 110.0, "status": raw["status"]})
        assert snap3.hash_conteudo == h2
        assert snap3.ultima_modificacao_detectada_em is not None