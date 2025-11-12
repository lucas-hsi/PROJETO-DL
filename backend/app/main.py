from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from time import time

from app.core.logger import configure_logging
from app.api.routes import api_router
from app.api.routes import health
from app.api.routes import meli_auth
from app.core.database import init_db

configure_logging()

app = FastAPI(title="DL Auto Peças API")

# CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
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


@app.on_event("shutdown")
def on_shutdown():
    pass


app.include_router(api_router)
app.include_router(health.router)
app.include_router(meli_auth.router, tags=["Mercado Livre"])