from typing import Optional
from sqlmodel import Session, select
from passlib.context import CryptContext

from app.models.usuario import Usuario


pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(senha_plana: str) -> str:
    return pwd.hash(senha_plana)


def verify_password(senha_plana: str, senha_hash: str) -> bool:
    return pwd.verify(senha_plana, senha_hash)


def get_by_email(session: Session, email: str) -> Optional[Usuario]:
    return session.exec(select(Usuario).where(Usuario.email == email)).first()


def create_if_not_exists(session: Session, email: str, senha_plana: str, role: str) -> Usuario:
    user = get_by_email(session, email)
    if user:
        return user
    user = Usuario(email=email, senha_hash=hash_password(senha_plana), role=role, is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
