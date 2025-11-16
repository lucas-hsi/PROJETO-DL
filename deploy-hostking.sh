#!/bin/bash
# Script de Deploy para HostKing - DL Auto Peças

set -e  # Sair em caso de erro

echo "🚀 Iniciando deploy para HostKing..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funções auxiliares
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar dependências
check_dependencies() {
    log_info "Verificando dependências..."
    
    command -v docker >/dev/null 2>&1 || { log_error "Docker não está instalado"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose não está instalado"; exit 1; }
    
    log_info "✅ Dependências verificadas"
}

# Criar arquivo .env se não existir
create_env_file() {
    if [ ! -f .env ]; then
        log_warn "Arquivo .env não encontrado, criando template..."
        cat > .env << EOF
# Configurações do Banco de Dados
POSTGRES_DB=dl_autopecas_prod
POSTGRES_USER=dl_admin
POSTGRES_PASSWORD=your_secure_password_here

# Configurações do Mercado Livre
ML_APP_ID=your_ml_app_id
ML_CLIENT_SECRET=your_ml_client_secret
ML_SELLER_ID=your_seller_id
ML_REDIRECT_URI=https://api.dlautopecas.com.br/auth/callback

# Configurações de Segurança
SECRET_KEY=your_super_secret_key_here_min_32_chars
WEBHOOK_SECRET=dl-auto-pecas-webhook-secret-2024

# URLs da Aplicação
BACKEND_URL=https://api.dlautopecas.com.br
NEXT_PUBLIC_API_URL=https://api.dlautopecas.com.br
NEXT_PUBLIC_SITE_URL=https://dlautopecas.com.br

# Configurações de Email (opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@dlautopecas.com.br
EOF
        log_warn "⚠️ Por favor, edite o arquivo .env com suas configurações reais!"
        exit 1
    fi
}

# Criar certificados SSL auto-assinados (temporário)
create_ssl_certificates() {
    if [ ! -f "nginx/ssl/cert.pem" ]; then
        log_info "Criando certificados SSL auto-assinados..."
        mkdir -p nginx/ssl
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=BR/ST=SP/L=SaoPaulo/O=DLAutoPecas/CN=dlautopecas.com.br"
        
        chmod 600 nginx/ssl/*.pem
        log_info "✅ Certificados SSL criados (substitua com certificados reais em produção)"
    else
        log_info "✅ Certificados SSL já existem"
    fi
}

# Build das imagens Docker
build_images() {
    log_info "Build das imagens Docker..."
    
    # Backend
    log_info "Building backend..."
    docker-compose -f docker-compose.prod.yml build backend
    
    # Frontend
    log_info "Building frontend..."
    docker-compose -f docker-compose.prod.yml build frontend
    
    # Scheduler
    log_info "Building scheduler..."
    docker-compose -f docker-compose.prod.yml build scheduler
    
    log_info "✅ Imagens construídas com sucesso"
}

# Deploy inicial
initial_deploy() {
    log_info "Realizando deploy inicial..."
    
    # Parar containers antigos se existirem
    docker-compose -f docker-compose.prod.yml down || true
    
    # Remover volumes antigos (cuidado: isso apaga dados!)
    # docker-compose -f docker-compose.prod.yml down -v || true
    
    # Subir serviços
    log_info "Subindo serviços..."
    docker-compose -f docker-compose.prod.yml up -d postgres redis
    
    # Aguardar banco iniciar
    log_info "Aguardando banco de dados iniciar..."
    sleep 10
    
    # Subir backend e frontend
    docker-compose -f docker-compose.prod.yml up -d backend frontend nginx
    
    # Aguardar serviços iniciarem
    log_info "Aguardando serviços iniciarem..."
    sleep 15
    
    # Subir scheduler
    docker-compose -f docker-compose.prod.yml up -d scheduler
    
    log_info "✅ Deploy inicial concluído"
}

# Verificar saúde dos serviços
check_health() {
    log_info "Verificando saúde dos serviços..."
    
    # Verificar containers
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_info "✅ Containers estão rodando"
    else
        log_error "❌ Alguns containers não estão rodando"
        docker-compose -f docker-compose.prod.yml ps
        exit 1
    fi
    
    # Testar backend
    if curl -f http://localhost:8000/healthz >/dev/null 2>&1; then
        log_info "✅ Backend está respondendo"
    else
        log_error "❌ Backend não está respondendo"
        exit 1
    fi
    
    # Testar frontend
    if curl -f http://localhost:3000 >/dev/null 2>&1; then
        log_info "✅ Frontend está respondendo"
    else
        log_error "❌ Frontend não está respondendo"
        exit 1
    fi
    
    log_info "✅ Todos os serviços estão saudáveis"
}

# Configurar webhooks externos
setup_webhooks() {
    log_info "Configurando webhooks..."
    
    # Obter configuração de webhooks
    WEBHOOK_CONFIG=$(curl -s http://localhost:8000/api/webhooks/importacao/config)
    
    if [ $? -eq 0 ]; then
        log_info "✅ Configuração de webhooks obtida"
        echo "$WEBHOOK_CONFIG" | jq '.'
        
        log_info "📋 Configurações de agendamento disponíveis:"
        echo "$WEBHOOK_CONFIG" | jq -r '.config.schedules[] | "\(.name): \(.cron)"'
        
        log_warn "⚠️ Configure estes webhooks no seu serviço de agendamento externo (Cron-job.org, etc)"
    else
        log_error "❌ Erro ao obter configuração de webhooks"
    fi
}

# Testar webhooks
test_webhooks() {
    log_info "Testando webhooks..."
    
    # Testar webhook de teste
    if curl -X POST http://localhost:8000/api/webhooks/importacao/test -H "Content-Type: application/json" | grep -q "success"; then
        log_info "✅ Webhook de teste funcionando"
    else
        log_error "❌ Webhook de teste falhou"
    fi
}

# Menu principal
main() {
    echo "🏁 DL Auto Peças - Deploy HostKing"
    echo "===================================="
    
    check_dependencies
    create_env_file
    create_ssl_certificates
    
    case "${1:-deploy}" in
        "build")
            build_images
            ;;
        "deploy")
            build_images
            initial_deploy
            check_health
            setup_webhooks
            test_webhooks
            ;;
        "health")
            check_health
            ;;
        "webhooks")
            setup_webhooks
            test_webhooks
            ;;
        "logs")
            docker-compose -f docker-compose.prod.yml logs -f
            ;;
        "stop")
            docker-compose -f docker-compose.prod.yml down
            ;;
        "restart")
            docker-compose -f docker-compose.prod.yml restart
            ;;
        *)
            echo "Uso: $0 [comando]"
            echo "Comandos disponíveis:"
            echo "  deploy    - Deploy completo (padrão)"
            echo "  build     - Build das imagens"
            echo "  health    - Verificar saúde dos serviços"
            echo "  webhooks  - Configurar e testar webhooks"
            echo "  logs      - Ver logs em tempo real"
            echo "  stop      - Parar todos os serviços"
            echo "  restart   - Reiniciar todos os serviços"
            exit 1
            ;;
    esac
    
    log_info "🎉 Deploy concluído com sucesso!"
    log_info "📍 Frontend: https://dlautopecas.com.br"
    log_info "📍 Backend API: https://api.dlautopecas.com.br"
    log_info "📍 Webhooks: https://api.dlautopecas.com.br/api/webhooks/importacao"
}

# Executar
main "$@"