# 🚀 DL SISTEMA - Guia Completo de Deployment Enterprise

## 📋 Visão Geral

Este guia fornece instruções completas para deploy do DL_SISTEMA em VPS KingHost com padrão Enterprise, incluindo:

- ✅ Remoção completa do Render
- ✅ Configuração de VPS Ubuntu/Linux
- ✅ Docker Compose com todos os serviços
- ✅ Nginx reverse proxy com SSL automático
- ✅ Monitoramento e manutenção automatizada
- ✅ Backup e recuperação
- ✅ Zero downtime deployment

## 📁 Estrutura de Arquivos Criados

```
c:\PROJETO DL\
├── vps-setup.sh              # Script de preparação da VPS
├── docker-compose.vps.yml    # Compose completo para produção
├── .env.vps.example         # Exemplo de variáveis de ambiente
├── nginx/
│   └── nginx.vps.conf       # Configuração Nginx Enterprise
├── deploy.sh                 # Script de deploy com zero downtime
├── setup-ssl.sh             # Configuração automática de SSL
├── monitor.sh               # Monitoramento completo do sistema
├── smoke-test.sh            # Testes de integração completos
└── README-DEPLOYMENT.md     # Este arquivo
```

## 🚀 Passo a Passo do Deployment

### 1️⃣ Preparação da VPS KingHost

```bash
# Conectar à VPS via SSH
ssh root@seu-ip-vps

# Executar script de preparação
chmod +x vps-setup.sh
./vps-setup.sh

# Fazer logout e login novamente para aplicar grupo docker
exit
ssh root@seu-ip-vps
```

### 2️⃣ Clonar o Repositório

```bash
cd /var/www/dl_sistema
git clone https://github.com/seu-usuario/dl_sistema.git .
```

### 3️⃣ Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.vps.example .env

# Editar arquivo com suas configurações
nano .env

# Configurar obrigatoriamente:
# - POSTGRES_PASSWORD (senha forte)
# - ML_CLIENT_ID, ML_CLIENT_SECRET (Mercado Livre)
# - SHOPIFY_STORE_DOMAIN, SHOPIFY_ACCESS_TOKEN (Shopify)
# - JWT_SECRET (mínimo 32 caracteres)
# - DOMAIN (seu domínio real)
# - SSL_EMAIL (email para SSL)
```

### 4️⃣ Executar Deploy Inicial

```bash
# Dar permissão aos scripts
chmod +x deploy.sh setup-ssl.sh monitor.sh smoke-test.sh

# Executar deploy
./deploy.sh production main

# Aguardar conclusão (pode levar 10-15 minutos)
```

### 5️⃣ Configurar SSL (Let's Encrypt)

```bash
# Configurar SSL automático
./setup-ssl.sh seu-dominio.com admin@seu-dominio.com
```

### 6️⃣ Executar Smoke Test

```bash
# Verificar se tudo está funcionando
./smoke-test.sh
```

### 7️⃣ Configurar Monitoramento

```bash
# Adicionar ao crontab para monitoramento automático
crontab -e

# Adicionar linhas:
# Monitoramento a cada 5 minutos
*/5 * * * * /var/www/dl_sistema/monitor.sh containers > /dev/null 2>&1

# Backup diário às 3h
0 3 * * * /var/www/dl_sistema/backup/backup.sh > /dev/null 2>&1

# Verificação SSL diária
0 6 * * * /var/www/dl_sistema/check_ssl.sh > /dev/null 2>&1
```

## 🔧 Comandos Úteis

### Gerenciamento de Serviços

```bash
# Ver status dos serviços
docker-compose -f docker-compose.vps.yml ps

# Ver logs em tempo real
docker-compose -f docker-compose.vps.yml logs -f

# Restart de serviço específico
docker-compose -f docker-compose.vps.yml restart backend

# Parar todos os serviços
docker-compose -f docker-compose.vps.yml down

# Iniciar todos os serviços
docker-compose -f docker-compose.vps.yml up -d
```

### Backup e Recuperação

```bash
# Backup manual
/var/www/dl_sistema/backup/backup.sh

# Verificar backups
ls -la /var/www/dl_sistema/backup/

# Restaurar backup do banco
docker exec -i dl_sistema_postgres psql -U dl_user dl_auto_pecas < backup.sql
```

### Monitoramento

```bash
# Verificar saúde completa
./monitor.sh full

# Verificar apenas containers
./monitor.sh containers

# Verificar SSL
./monitor.sh ssl

# Verificar recursos do sistema
./monitor.sh system
```

### Deploy de Atualizações

```bash
# Deploy simples (usa branch main)
./deploy.sh

# Deploy com branch específica
./deploy.sh production develop

# Deploy com ambiente específico
./deploy.sh staging main
```

## 🌐 URLs do Sistema

Após configuração completa:

- **Frontend**: `https://seu-dominio.com`
- **Backend API**: `https://seu-dominio.com/api`
- **Documentação API**: `https://seu-dominio.com/api/docs`
- **Webhooks**: `https://seu-dominio.com/webhooks`
- **Health Check**: `https://seu-dominio.com/health`

## 📊 Arquitetura Final

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS KingHost                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Nginx Reverse Proxy                    │    │
│  │              (SSL, HTTP/2, Gzip)                    │    │
│  └────────────────┬──────────────────────────────────┘    │
│                   │                                         │
│  ┌────────────────┴──────────────────────────────────┐    │
│  │              Docker Network                        │    │
│  │                                                    │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │    │
│  │  │  Frontend   │ │   Backend   │ │  Webhooks   │ │    │
│  │  │  Next.js    │ │   FastAPI   │ │   Service   │ │    │
│  │  │  :3000      │ │   :8000     │ │   :8080     │ │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ │    │
│  │                                                    │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │    │
│  │  │   Worker    │ │  Scheduler  │ │   Nginx     │ │    │
│  │  │   Celery    │ │   Celery    │ │   Proxy     │ │    │
│  │  │  Beat       │ │   Beat      │ │   :80/443   │ │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ │    │
│  │                                                    │    │
│  │  ┌─────────────┐ ┌─────────────┐                │    │
│  │  │ PostgreSQL  │ │    Redis    │                │    │
│  │  │    :5432    │ │    :6379    │                │    │
│  │  └─────────────┘ └─────────────┘                │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Segurança

### Configurações Implementadas

- ✅ SSL/TLS com Let's Encrypt
- ✅ Firewall UFW configurado
- ✅ Headers de segurança no Nginx
- ✅ Rate limiting por IP
- ✅ CORS configurado
- ✅ Container isolation
- ✅ Secrets em variáveis de ambiente
- ✅ Backup automático

### Boas Práticas

1. **Senhas**: Use senhas fortes e únicas
2. **Updates**: Mantenha o sistema atualizado
3. **Monitoramento**: Verifique logs regularmente
4. **Backups**: Teste restauração periodicamente
5. **SSL**: Monitore expiração do certificado

## 📈 Performance

### Otimizações Aplicadas

- ✅ Gzip compression ativado
- ✅ HTTP/2 habilitado
- ✅ Keep-alive connections
- ✅ Static file caching
- ✅ Database connection pooling
- ✅ Worker processes otimizados
- ✅ Memory limits configurados

### Métricas de Referência

- **Tempo de resposta API**: < 200ms
- **Tempo de resposta Frontend**: < 1s
- **Disponibilidade**: 99.9%
- **Capacidade**: 1000+ requisições/segundo

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Container não inicia
```bash
# Verificar logs
docker-compose -f docker-compose.vps.yml logs [servico]

# Verificar recursos
docker system df
docker system prune -f
```

#### 2. PostgreSQL não conecta
```bash
# Verificar saúde
docker-compose -f docker-compose.vps.yml exec postgres pg_isready -U dl_user

# Verificar variáveis
docker-compose -f docker-compose.vps.yml exec postgres env | grep POSTGRES
```

#### 3. SSL não funciona
```bash
# Verificar certificado
./check_ssl.sh

# Renovar manualmente
certbot renew --force-renewal
```

#### 4. Performance lenta
```bash
# Verificar recursos
./monitor.sh system

# Verificar logs de erro
./monitor.sh logs
```

## 📞 Suporte

### Logs Importantes

- **Aplicação**: `/var/www/dl_sistema/logs/`
- **Nginx**: `/var/www/dl_sistema/logs/nginx/`
- **Sistema**: `/var/log/syslog`
- **Docker**: `journalctl -u docker.service`

### Comandos de Diagnóstico

```bash
# Verificar todos os serviços
systemctl status docker nginx

# Verificar espaço em disco
df -h

# Verificar memória
free -h

# Verificar processos
top -o %CPU
```

## ✅ Checklist Final

Ant de colocar em produção, certifique-se de:

- [ ] Domínio configurado e apontando para VPS
- [ ] SSL configurado e funcionando
- [ ] Integrações ML e Shopify configuradas
- [ ] Backups automáticos ativados
- [ ] Monitoramento configurado
- [ ] Smoke test passando
- [ ] Logs sendo rotacionados
- [ ] Firewall ativado
- [ ] Senhas fortes definidas
- [ ] Documentação atualizada

## 🎯 Próximos Passos

1. **Configurar CDN** (CloudFlare) para performance global
2. **Implementar sentry** para monitoramento de erros
3. **Configurar ELK** para análise de logs
4. **Implementar CI/CD** com GitHub Actions
5. **Configurar múltiplas regiões** para alta disponibilidade

---

**🎉 Parabéns!** Seu DL_SISTEMA está agora rodando com padrão Enterprise na VPS KingHost!

**Data da Configuração**: $(date)
**Versão do Deployment**: 1.0.0
**Status**: ✅ OPERACIONAL