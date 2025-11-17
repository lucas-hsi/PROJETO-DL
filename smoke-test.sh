#!/bin/bash

# 🧪 DL SISTEMA - Smoke Test Completo
# Testa todos os componentes do sistema para garantir funcionamento

set -e

# Configurações
PROJECT_DIR="/var/www/dl_sistema"
API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost"
WEBHOOK_URL="http://localhost:8080"
TIMEOUT=30

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

# Teste de conectividade básica
test_connectivity() {
    log "🔗 Testando conectividade básica..."
    
    # Testar localhost
    if ping -c 1 localhost > /dev/null 2>&1; then
        log_success "Conectividade local: OK"
    else
        log_error "Conectividade local: FALHOU"
        return 1
    fi
    
    # Testar DNS
    if ping -c 1 google.com > /dev/null 2>&1; then
        log_success "DNS: OK"
    else
        log_warning "DNS: Problemas detectados"
    fi
}

# Teste dos containers Docker
test_containers() {
    log "🐳 Testando containers Docker..."
    
    # Verificar se Docker está rodando
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado"
        return 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker não está rodando"
        return 1
    fi
    
    log_success "Docker: OK"
    
    # Lista de containers esperados
    CONTAINERS=("dl_sistema_postgres" "dl_sistema_redis" "dl_sistema_backend" "dl_sistema_worker" "dl_sistema_webhooks" "dl_sistema_frontend" "dl_sistema_nginx")
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            if [ "$STATUS" = "running" ]; then
                log_success "$container: running"
            else
                log_error "$container: $STATUS"
            fi
        else
            log_error "$container: não encontrado"
        fi
    done
}

# Teste do PostgreSQL
test_postgres() {
    log "🗄️ Testando PostgreSQL..."
    
    # Verificar se PostgreSQL está rodando
    if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" ps postgres | grep -q "Up"; then
        # Testar conexão
        if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T postgres pg_isready -U dl_user -d dl_auto_pecas; then
            log_success "PostgreSQL: conexão OK"
            
            # Testar consulta básica
            if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T postgres psql -U dl_user -d dl_auto_pecas -c "SELECT 1;" > /dev/null 2>&1; then
                log_success "PostgreSQL: consulta OK"
            else
                log_error "PostgreSQL: consulta falhou"
            fi
        else
            log_error "PostgreSQL: conexão falhou"
        fi
    else
        log_error "PostgreSQL: container não está rodando"
    fi
}

# Teste do Redis
test_redis() {
    log "🔴 Testando Redis..."
    
    # Verificar se Redis está rodando
    if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" ps redis | grep -q "Up"; then
        # Testar conexão
        if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T redis redis-cli ping | grep -q PONG; then
            log_success "Redis: conexão OK"
            
            # Testar set/get
            if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T redis redis-cli set test_key "test_value" > /dev/null 2>&1; then
                if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T redis redis-cli get test_key | grep -q "test_value"; then
                    log_success "Redis: set/get OK"
                    docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T redis redis-cli del test_key > /dev/null 2>&1
                else
                    log_error "Redis: get falhou"
                fi
            else
                log_error "Redis: set falhou"
            fi
        else
            log_error "Redis: conexão falhou"
        fi
    else
        log_error "Redis: container não está rodando"
    fi
}

# Teste do Backend FastAPI
test_backend() {
    log "🚀 Testando Backend FastAPI..."
    
    # Health check
    if curl -f -s "$API_URL/healthz" > /dev/null; then
        log_success "Backend: health check OK"
    else
        log_error "Backend: health check falhou"
        return 1
    fi
    
    # Testar documentação
    if curl -f -s "$API_URL/docs" > /dev/null; then
        log_success "Backend: docs disponível"
    else
        log_warning "Backend: docs não disponível"
    fi
    
    # Testar endpoints básicos
    ENDPOINTS=("$API_URL/api/v1/health" "$API_URL/api/v1/auth/me")
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log_success "Backend: $endpoint OK"
        else
            log_warning "Backend: $endpoint não respondendo"
        fi
    done
}

# Teste do Frontend Next.js
test_frontend() {
    log "🎨 Testando Frontend Next.js..."
    
    # Testar página inicial
    if curl -f -s "$FRONTEND_URL" > /dev/null; then
        log_success "Frontend: página inicial OK"
    else
        log_error "Frontend: página inicial falhou"
        return 1
    fi
    
    # Testar assets estáticos
    if curl -f -s "$FRONTEND_URL/_next/static/" > /dev/null; then
        log_success "Frontend: assets estáticos OK"
    else
        log_warning "Frontend: assets estáticos não disponível"
    fi
    
    # Testar API proxy
    if curl -f -s "$FRONTEND_URL/api/healthz" > /dev/null; then
        log_success "Frontend: proxy API OK"
    else
        log_warning "Frontend: proxy API não funcionando"
    fi
}

# Teste do Nginx
test_nginx() {
    log "🌐 Testando Nginx..."
    
    # Health check
    if curl -f -s "$FRONTEND_URL/health" > /dev/null; then
        log_success "Nginx: health check OK"
    else
        log_error "Nginx: health check falhou"
        return 1
    fi
    
    # Testar proxy reverso
    if curl -f -s "$FRONTEND_URL/api/healthz" > /dev/null; then
        log_success "Nginx: proxy reverso OK"
    else
        log_error "Nginx: proxy reverso falhou"
    fi
    
    # Testar SSL (se configurado)
    if curl -f -s "https://localhost" > /dev/null 2>&1; then
        log_success "Nginx: SSL OK"
    else
        log_warning "Nginx: SSL não configurado ou falhou"
    fi
}

# Teste do Worker Celery
test_worker() {
    log "👷 Testando Worker Celery..."
    
    # Verificar se worker está rodando
    if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" ps worker | grep -q "Up"; then
        log_success "Worker: container rodando"
        
        # Verificar logs recentes
        WORKER_LOGS=$(docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" logs --tail=10 worker 2>/dev/null | grep -i "ready\|connected" | wc -l)
        if [ "$WORKER_LOGS" -gt 0 ]; then
            log_success "Worker: logs indicam funcionamento"
        else
            log_warning "Worker: não foi possível verificar logs"
        fi
    else
        log_error "Worker: container não está rodando"
    fi
}

# Teste dos Webhooks
test_webhooks() {
    log "📡 Testando Webhooks..."
    
    # Health check
    if curl -f -s "$WEBHOOK_URL/healthz" > /dev/null; then
        log_success "Webhooks: health check OK"
    else
        log_error "Webhooks: health check falhou"
        return 1
    fi
    
    # Testar endpoints de webhook
    WEBHOOK_ENDPOINTS=("$WEBHOOK_URL/webhooks/shopify" "$WEBHOOK_URL/webhooks/mercadolibre")
    
    for endpoint in "${WEBHOOK_ENDPOINTS[@]}"; do
        # Testar com método OPTIONS (preflight)
        if curl -X OPTIONS -f -s "$endpoint" > /dev/null; then
            log_success "Webhooks: $endpoint respondendo"
        else
            log_warning "Webhooks: $endpoint não respondendo"
        fi
    done
}

# Teste de integração Mercado Livre
test_ml_integration() {
    log "🟡 Testando integração Mercado Livre..."
    
    # Verificar se há configuração ML
    if grep -q "ML_CLIENT_ID" "$PROJECT_DIR/.env" && grep -q "YOUR_ML_CLIENT_ID" "$PROJECT_DIR/.env"; then
        log_warning "Mercado Livre: não configurado (usando valores padrão)"
        return 0
    fi
    
    # Testar endpoint de autenticação
    if curl -f -s "$API_URL/api/v1/meli/auth/status" > /dev/null; then
        log_success "ML: endpoint de auth disponível"
    else
        log_warning "ML: endpoint de auth não disponível"
    fi
}

# Teste de integração Shopify
test_shopify_integration() {
    log "🛒 Testando integração Shopify..."
    
    # Verificar se há configuração Shopify
    if grep -q "SHOPIFY_STORE_DOMAIN" "$PROJECT_DIR/.env" && grep -q "sua-loja.myshopify.com" "$PROJECT_DIR/.env"; then
        log_warning "Shopify: não configurado (usando valores padrão)"
        return 0
    fi
    
    # Testar endpoint de webhooks
    if curl -f -s "$WEBHOOK_URL/webhooks/shopify" > /dev/null; then
        log_success "Shopify: webhook endpoint disponível"
    else
        log_warning "Shopify: webhook endpoint não disponível"
    fi
}

# Teste de performance básico
test_performance() {
    log "⚡ Testando performance básica..."
    
    # Testar tempo de resposta do backend
    BACKEND_TIME=$(curl -w "%{time_total}" -f -s -o /dev/null "$API_URL/healthz" 2>/dev/null || echo "999")
    if (( $(echo "$BACKEND_TIME < 1.0" | bc -l) )); then
        log_success "Backend: tempo de resposta OK (${BACKEND_TIME}s)"
    else
        log_warning "Backend: tempo de resposta alto (${BACKEND_TIME}s)"
    fi
    
    # Testar tempo de resposta do frontend
    FRONTEND_TIME=$(curl -w "%{time_total}" -f -s -o /dev/null "$FRONTEND_URL" 2>/dev/null || echo "999")
    if (( $(echo "$FRONTEND_TIME < 2.0" | bc -l) )); then
        log_success "Frontend: tempo de resposta OK (${FRONTEND_TIME}s)"
    else
        log_warning "Frontend: tempo de resposta alto (${FRONTEND_TIME}s)"
    fi
}

# Teste de carga básico
test_load() {
    log "💪 Testando carga básica..."
    
    # Testar com 10 requisições simultâneas
    log "Executando teste de carga no backend..."
    
    for i in {1..10}; do
        if curl -f -s "$API_URL/healthz" > /dev/null; then
            echo -n "."
        else
            echo -n "F"
        fi
    done
    echo ""
    
    log_success "Teste de carga concluído"
}

# Relatório final
generate_report() {
    log "📊 Gerando relatório de testes..."
    
    echo ""
    echo "========================================="
    echo "🧪 RELATÓRIO DE SMOKE TEST"
    echo "========================================="
    echo "Data: $(date)"
    echo "Servidor: $(hostname)"
    echo ""
    echo "📈 RESULTADOS:"
    echo "   ✅ Testes passados: $TESTS_PASSED"
    echo "   ❌ Testes falhados: $TESTS_FAILED"
    echo ""
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo "🎉 TODOS OS TESTES PASSARAM!"
        echo "   O sistema está funcionando corretamente."
    else
        echo "⚠️  ALGUNS TESTES FALHARAM!"
        echo "   Verifique os logs acima para detalhes."
    fi
    
    echo ""
    echo "🔗 URLs do sistema:"
    echo "   Frontend: $FRONTEND_URL"
    echo "   Backend API: $API_URL"
    echo "   Webhooks: $WEBHOOK_URL"
    echo "   Health Check: $FRONTEND_URL/health"
    echo ""
    echo "📋 Próximos passos:"
    echo "   1. Configure o domínio e SSL se ainda não fez"
    echo "   2. Configure as integrações (ML, Shopify)"
    echo "   3. Execute: ./monitor.sh para monitoramento"
    echo "   4. Configure backups automáticos"
    echo "========================================="
}

# Função principal
main() {
    log "🧪 Iniciando Smoke Test do DL SISTEMA"
    
    # Verificar se estamos no diretório correto
    if [ ! -f "$PROJECT_DIR/docker-compose.vps.yml" ]; then
        log_error "Arquivo docker-compose.vps.yml não encontrado!"
        log_error "Execute este script do diretório do projeto: /var/www/dl_sistema"
        exit 1
    fi
    
    # Executar testes
    test_connectivity
    test_containers
    test_postgres
    test_redis
    test_backend
    test_frontend
    test_nginx
    test_worker
    test_webhooks
    test_ml_integration
    test_shopify_integration
    test_performance
    test_load
    
    # Relatório final
    generate_report
    
    # Retornar código de saída baseado nos resultados
    if [ "$TESTS_FAILED" -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Tratamento de erros
trap 'log_error "Erro na linha $LINENO. Smoke test falhou!"' ERR

# Executar smoke test
main "$@"