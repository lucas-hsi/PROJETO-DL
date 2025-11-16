# PROJETO DL

Monorepo do sistema DL Auto Peças com backend (FastAPI), frontend (Next.js + TypeScript) e módulo de produtos/documentação. Infra orquestrada via Docker Compose, pronta para desenvolvimento local e provisionamento em nuvem.

## Stack
- Backend: FastAPI (Python 3.11), SQLModel, PostgreSQL
- Worker: Celery + Redis
- Frontend: Next.js + TypeScript (Node 20)
- Infra: Docker Compose, .env

## Tecnologias e Padrões
- APIs e serviços modularizados: `app/api/routes/**`, `app/services/**`
- Integração Mercado Livre (OAuth2, importação completa, incremental e recentes)
- Logs estruturados (JSON) e health checks (`/healthz`, `/healthz/db`)
- UI/UX premium com layout consistente e cabeçalho degradê para Anunciador
- Scripts padronizados para build/start e deploy gerenciado

## Serviços
- `backend`: API FastAPI com hot reload em `http://localhost:8000`
- `worker`: Celery conectado ao Redis (tarefa `ping`)
- `frontend`: Next.js com hot reload em `http://localhost:3000`
- `postgres`: Banco de dados PostgreSQL
- `redis`: Fila para Celery

### Endpoints principais
- `GET /healthz` — status, uptime e versão
- `GET /healthz/db` — verificação de banco
- `GET /diagnostics/meli/*` — diagnósticos de integração ML
- `POST /auth/login` — autenticação e perfil
- `GET /estoque` — listagem com paginação
- `POST /estoque/importar-meli-todos-status` — importação completa (todos os status)
- `POST /estoque/importar-meli-incremental?hours=24` — importação de recentes
- `POST /meli/sync/incremental-start` — sincronização incremental em background

## Subpastas
- `backend/` — Aplicação FastAPI e worker Celery
- `frontend/` — Aplicação Next.js + TS
- `produtos/` — Documentação e modelos de dados

## Webhooks
- Rotas: `backend/app/api/routes/webhooks.py`
- Objetivo: disparo de sincronização/importação automática via integrações externas
- Segurança: validação de cabeçalhos e tokens (config via `.env`)
- Log: todos eventos são registrados via `app.core.logger`

## Setup rápido
1. Copie `.env.example` para `.env` e ajuste se necessário.
2. Suba os serviços:
   ```bash
   docker compose up --build
   ```
3. Teste de fumaça:
   - `http://localhost:8000/healthz` → deve retornar `{status:"ok"}`
   - `http://localhost:3000` → deve exibir “API Online”

## Variáveis de Ambiente (.env)
- Banco: `DATABASE_URL=postgresql+psycopg2://user:pass@host:port/db`
- Mercado Livre: `ML_CLIENT_ID`, `ML_CLIENT_SECRET`, `ML_REDIRECT_URI`, `ML_SELLER_ID`, `ML_API_BASE_URL`
- App: `APP_VERSION`, chaves de segurança JWT

## Scripts de Build/Start
Frontend:
- `npm run build`
- `npm run start`

Backend (produção):
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`

Arquivos de deploy:
- `Procfile`: `web: sh start.sh`
- `start.sh`: inicia backend (Uvicorn) e frontend (Next.js) respeitando `.env`

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

## Deploy na KingHost
- Usar Node LTS (v18/v20) para build do Next.js
- Backend via Uvicorn sem hot-reload, com workers definidos
- Variáveis de ambiente definidas pelo provedor (respeitadas pelo `start.sh`)
- Logs essenciais, sem modo debug em produção

## Fluxos de Importação (Mercado Livre)
- Completa: importa todos os produtos em múltiplos status
- Recentes (24h): sincroniza atualizações recentes
- Incremental: processo em background, com consulta periódica de status

## Painel Anunciador — Estoque
- Cabeçalho com degradê roxo premium
- Filtros e barra de busca com debounce
- Botão “Apenas importação completa” para importação full
- Tabela com atualização estável

## Rollback
```bash
docker compose down -v
make init-db
```

## Notas
- Login multi-perfil (Gestor, Vendedor, Anúncios) com redirecionamento está em progresso.
- Rotas e serviços são modularizados conforme `app/api/routes` e `app/services`.

## Processo e Atualizações
- Política: sem mocks, sempre conectado ao banco
- Projeto roda com `docker-compose up` sem configs extras
- Layout premium, sidebar flutuante, UX/UI consistente
- Isolamento do módulo `/anunciador/estoque` garantido para deploy