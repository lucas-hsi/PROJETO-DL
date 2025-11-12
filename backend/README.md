# Backend (FastAPI)

API FastAPI com SQLModel, PostgreSQL, Celery + Redis e logs estruturados.

## Endpoints
- `GET /healthz` — status, uptime e versão
- `GET /estoque` — lista produtos com paginação e ordenação
- `POST /estoque` — cria produto (SKU único)

## Desenvolvimento
Serviço roda via docker compose com hot reload. Configurações em `app/core/config.py`.

## Testes
```bash
make test
```

## Seed Mercado Livre
```bash
make init-db
```