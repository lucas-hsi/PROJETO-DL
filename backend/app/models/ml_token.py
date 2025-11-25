from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class MlToken(SQLModel, table=True):
    __tablename__ = "ml_tokens"
    id: Optional[int] = Field(default=1, primary_key=True)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)