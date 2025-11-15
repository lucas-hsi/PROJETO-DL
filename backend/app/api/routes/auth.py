from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.repositories.usuario_repo import get_by_email, verify_password
from app.core.security import create_access_token, get_current_user_from_token


router = APIRouter(prefix="/auth")


class LoginInput(BaseModel):
    email: str
    senha: str


@router.post("/login")
def login(payload: LoginInput, session: Session = Depends(get_session)):
    user = get_by_email(session, payload.email)
    if not user or not verify_password(payload.senha, user.senha_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "role": user.role, "uid": user.id})
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/me")
def me(claims: dict = Depends(get_current_user_from_token)):
    return {"email": claims.get("sub"), "role": claims.get("role"), "uid": claims.get("uid")}
