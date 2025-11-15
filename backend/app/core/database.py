from typing import Generator
from sqlmodel import SQLModel, create_engine, Session
import time
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logger import logger


def _get_engine():
    settings = get_settings()
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL aponta para SQLite. O backend deve usar PostgreSQL.")
    engine = create_engine(url, pool_pre_ping=True)
    return engine


engine = _get_engine()


def init_db():
    settings = get_settings()
    start = time.time()
    deadline = start + 30
    last_err = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("DATABASE CONNECTED: POSTGRESQL")
            break
        except OperationalError as e:
            last_err = e
            logger.error({"event": "DB_CONNECT_RETRY", "error": str(e)})
            time.sleep(2)
    else:
        logger.error({"event": "DB_CONNECT_FATAL", "error": str(last_err)})
        raise last_err

    SQLModel.metadata.create_all(engine)
    logger.info("Database tables ensured.")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session