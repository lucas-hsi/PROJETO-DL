from typing import Optional, Dict
from datetime import datetime

from sqlmodel import Session, select

from app.models.meli_item_snapshot import MeliItemSnapshot


def get_snapshot_by_meli_id(session: Session, meli_id: str) -> Optional[MeliItemSnapshot]:
    return session.exec(select(MeliItemSnapshot).where(MeliItemSnapshot.meli_id == meli_id)).first()


def get_snapshot_by_sku(session: Session, sku: str) -> Optional[MeliItemSnapshot]:
    return session.exec(select(MeliItemSnapshot).where(MeliItemSnapshot.sku == sku)).first()


def upsert_snapshot_new(session: Session, sku: str, meli_id: str, hash_conteudo: str, status_meli: str, raw_payload: Dict | None) -> MeliItemSnapshot:
    snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
    now = datetime.utcnow()
    if snap:
        snap.sku = sku
        snap.meli_id = meli_id
        snap.hash_conteudo = hash_conteudo
        snap.status_meli = status_meli
        snap.ultima_sincronizacao_em = now
        snap.ultima_modificacao_detectada_em = now
        snap.raw_payload = raw_payload
        session.add(snap)
        session.commit()
        session.refresh(snap)
        return snap

    snap = MeliItemSnapshot(
        sku=sku,
        meli_id=meli_id,
        hash_conteudo=hash_conteudo,
        status_meli=status_meli,
        primeira_importacao_em=now,
        ultima_sincronizacao_em=now,
        ultima_modificacao_detectada_em=now,
        raw_payload=raw_payload,
    )
    session.add(snap)
    session.commit()
    session.refresh(snap)
    return snap


def mark_snapshot_unchanged(session: Session, snap: MeliItemSnapshot) -> MeliItemSnapshot:
    snap.ultima_sincronizacao_em = datetime.utcnow()
    session.add(snap)
    session.commit()
    session.refresh(snap)
    return snap


def update_snapshot_changed(session: Session, snap: MeliItemSnapshot, new_hash: str, status_meli: str, raw_payload: Dict | None) -> MeliItemSnapshot:
    now = datetime.utcnow()
    snap.hash_conteudo = new_hash
    snap.status_meli = status_meli
    snap.ultima_sincronizacao_em = now
    snap.ultima_modificacao_detectada_em = now
    snap.raw_payload = raw_payload
    session.add(snap)
    session.commit()
    session.refresh(snap)
    return snap