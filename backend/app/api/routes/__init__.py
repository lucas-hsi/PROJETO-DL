from fastapi import APIRouter
from .estoque import router as estoque_router
from .webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(estoque_router)
api_router.include_router(webhooks_router)