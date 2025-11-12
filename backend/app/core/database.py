from typing import Generator
from sqlmodel import SQLModel, create_engine, Session

from app.core.config import get_settings
from app.core.logger import logger


def _get_engine():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return engine


engine = _get_engine()


def init_db():
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created.")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session