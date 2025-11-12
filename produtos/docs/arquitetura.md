# Arquitetura

Sistema DL Auto Peças é composto por:

- Backend FastAPI (Python 3.11)
- Frontend Next.js (Node 20)
- Banco PostgreSQL
- Fila Celery com Redis

Monorepo com `docker-compose` para orquestração e variáveis em `.env`.
Rotas e serviços modularizados para clareza e manutenção por devs júnior.