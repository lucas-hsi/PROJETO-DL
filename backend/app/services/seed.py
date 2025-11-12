from sqlmodel import Session

from app.core.database import engine
from app.core.config import get_settings
from app.core.logger import logger
from app.services.mercadolivre import seed_from_mercadolivre


def main():
    settings = get_settings()
    with Session(engine) as session:
        limit = settings.MERCADOLIVRE_SEED_LIMIT
        seed_from_mercadolivre(session, limit=limit)
    logger.info({"event": "seed_completed"})


if __name__ == "__main__":
    main()