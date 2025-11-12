# PROJETO DL

Monorepo do sistema DL Auto Peças com backend (FastAPI), frontend (Next.js + TypeScript) e módulo de produtos/documentação. Infra orquestrada via Docker Compose, pronta para desenvolvimento local e provisionamento em nuvem.

## Stack
- Backend: FastAPI (Python 3.11), SQLModel, PostgreSQL
- Worker: Celery + Redis
- Frontend: Next.js + TypeScript (Node 20)
- Infra: Docker Compose, .env

## Serviços
- `backend`: API FastAPI com hot reload em `http://localhost:8000`
- `worker`: Celery conectado ao Redis (tarefa `ping`)
- `frontend`: Next.js com hot reload em `http://localhost:3000`
- `postgres`: Banco de dados PostgreSQL
- `redis`: Fila para Celery

## Subpastas
- `backend/` — Aplicação FastAPI e worker Celery
- `frontend/` — Aplicação Next.js + TS
- `produtos/` — Documentação e modelos de dados

## Setup rápido
1. Copie `.env.example` para `.env` e ajuste se necessário.
2. Suba os serviços:
   ```bash
   docker compose up --build
   ```
3. Teste de fumaça:
   - `http://localhost:8000/healthz` → deve retornar `{status:"ok"}`
   - `http://localhost:3000` → deve exibir “API Online”

## Banco inicial (Mercado Livre)
Para popular produtos iniciais a partir da API Mercado Livre:
```bash
make init-db
```
Este comando cria as tabelas e executa o seed público via serviço `mercadolivre`.

## Testes
Execute os testes do backend:
```bash
make test
```

## Rollback
```bash
docker compose down -v
make init-db
```

## Notas
- Login multi-perfil será implementado em iteração seguinte (Gestor, Vendedor, Anúncios) com redirecionamento.
- Rotas e serviços são modularizados conforme `app/api/routes` e `app/services`.