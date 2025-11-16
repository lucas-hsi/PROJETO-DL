from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from time import time

from app.core.logger import configure_logging
from app.api.routes import api_router
from app.api.routes import health
from app.api.routes import auth
from app.models.usuario import Usuario
from app.models.ml_log import MLLog
from app.models.meli_item_snapshot import MeliItemSnapshot
from app.models.meli_full_sync_job import MeliFullSyncJob
from app.repositories.usuario_repo import create_if_not_exists
from app.core.database import get_session
from app.api.routes import meli_auth
from app.api.routes import meli_test
from app.api.routes import diagnostics
from app.api.routes import meli_sync
from app.api.routes import meli_token
from app.core.database import init_db, engine
from sqlmodel import Session
from sqlalchemy import text
from fastapi import APIRouter

configure_logging()

app = FastAPI(title="DL Auto Peças API")

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://0.0.0.0:3000",
    "http://0.0.0.0:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de log simples para rastrear requisições
logger = logging.getLogger("uvicorn")

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"[REQ] {request.method} {request.url}")
    resp = await call_next(request)
    logger.info(f"[RES] {resp.status_code} {request.url.path}")
    return resp


@app.on_event("startup")
def on_startup():
    app.state.start_time = time()
    # Garante criação das tabelas ao iniciar a aplicação
    init_db()
    try:
        with Session(engine) as session:
            create_if_not_exists(session, "vendedor@dl.com", "123456", "vendedor")
            create_if_not_exists(session, "anunciador@dl.com", "123456", "anunciador")
            create_if_not_exists(session, "gestor@dl.com", "123456", "gestor")
    except Exception:
        pass
    
    # Inicia o monitoramento de tokens em background
    try:
        import asyncio
        from app.services.token_monitor import start_token_monitor
        
        def start_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_token_monitor())
            loop.close()
        
        # Executa em thread separada para não bloquear o startup
        import threading
        monitor_thread = threading.Thread(target=start_monitor, daemon=True)
        monitor_thread.start()
        
        logger.info("Monitoramento de tokens iniciado em background")
    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento de tokens: {e}")


@app.on_event("shutdown")
def on_shutdown():
    pass


app.include_router(api_router)
app.include_router(health.router)
app.include_router(meli_auth.router, tags=["Mercado Livre"])
app.include_router(meli_test.router, tags=["Mercado Livre Test"])
app.include_router(diagnostics.router, tags=["Diagnostics"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(meli_sync.router, tags=["Meli Sync"])
app.include_router(meli_token.router, tags=["Mercado Livre - Token Management"])

# Importar e adicionar rotas de webhooks
from app.api.routes import webhooks
app.include_router(webhooks.router, tags=["Webhooks"], prefix="/api")

db_health = APIRouter()

@db_health.get("/healthz/db")
def healthz_db():
    try:
        with Session(engine) as s:
            s.exec(text("SELECT 1"))
        return {"database": "postgres", "status": "ok"}
    except Exception:
        return {"database": "postgres", "status": "fail"}

app.include_router(db_health)
