from celery import Celery
from app.core.config import get_settings


settings = get_settings()
celery_app = Celery(
    "projeto_dl",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)


@celery_app.task(name="ping")
def ping():
    return "pong"