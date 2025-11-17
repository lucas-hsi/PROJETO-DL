#!/bin/bash

# 🚀 DL SISTEMA - Deployment Script
# Script completo para deploy com zero downtime
# Uso: ./deploy.sh [environment] [branch]

set -e

# Configurações
PROJECT_DIR="/var/www/dl_sistema"
BACKUP_DIR="/var/www/dl_sistema/backup"
LOG_FILE="/var/www/dl_sistema/logs/deploy.log"
ENVIRONMENT=${1:-production}
BRANCH=${2:-main}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"
}

# Verificações iniciais
check_requirements() {
    log "🔍 Verificando requisitos..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado"
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose não está instalado"
        exit 1
    fi
    
    # Verificar espaço em disco
    AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
    if [ "$AVAILABLE_SPACE" -lt 1048576 ]; then # 1GB em KB
        log_warning "Espaço em disco baixo: $(($AVAILABLE_SPACE / 1024))MB disponíveis"
    fi
    
    # Verificar se está no diretório correto
    if [ ! -f "docker-compose.vps.yml" ]; then
        log_error "docker-compose.vps.yml não encontrado. Execute o script do diretório do projeto."
        exit 1
    fi
    
    log_success "Requisitos verificados"
}

# Backup do banco de dados
backup_database() {
    log "💾 Criando backup do banco de dados..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Verificar se o PostgreSQL está rodando
    if docker-compose -f docker-compose.vps.yml ps postgres | grep -q "Up"; then
        docker-compose -f docker-compose.vps.yml exec -T postgres pg_dump -U ${POSTGRES_USER:-dl_user} ${POSTGRES_DB:-dl_auto_pecas} > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"
        log_success "Backup do banco criado: db_backup_$TIMESTAMP.sql"
    else
        log_warning "PostgreSQL não está rodando, pulando backup"
    fi
}

# Pull das novas imagens
pull_updates() {
    log "📥 Baixando atualizações..."
    
    # Git pull
    if [ -d ".git" ]; then
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
        log_success "Código atualizado do branch $BRANCH"
    else
        log_warning "Não é um repositório git, pulando atualização"
    fi
}

# Build das imagens Docker
build_images() {
    log "🔨 Construindo imagens Docker..."
    
    # Build com cache
    docker-compose -f docker-compose.vps.yml build --parallel
    
    log_success "Imagens construídas com sucesso"
}

# Deploy com zero downtime
deploy_services() {
    log "🚀 Iniciando deploy com zero downtime..."
    
    # Parar apenas os serviços que serão atualizados
    log "Parando serviços antigos..."
    docker-compose -f docker-compose.vps.yml stop backend worker webhooks scheduler
    
    # Iniciar novos serviços
    log "Iniciando novos serviços..."
    docker-compose -f docker-compose.vps.yml up -d --remove-orphans
    
    # Aguardar serviços ficarem prontos
    log "Aguardando serviços ficarem prontos..."
    sleep 30
    
    # Verificar saúde dos serviços
    check_health
    
    log_success "Deploy concluído com sucesso"
}

# Verificação de saúde dos serviços
check_health() {
    log "🏥 Verificando saúde dos serviços..."
    
    # Verificar backend
    if curl -f -s http://localhost:8000/healthz > /dev/null; then
        log_success "Backend está saudável"
    else
        log_error "Backend não está respondendo"
        return 1
    fi
    
    # Verificar webhooks
    if curl -f -s http://localhost:8080/healthz > /dev/null; then
        log_success "Webhooks está saudável"
    else
        log_error "Webhooks não está respondendo"
        return 1
    fi
    
    # Verificar nginx
    if curl -f -s http://localhost/health > /dev/null; then
        log_success "Nginx está saudável"
    else
        log_error "Nginx não está respondendo"
        return 1
    fi
    
    # Verificar PostgreSQL
    if docker-compose -f docker-compose.vps.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-dl_user} -d ${POSTGRES_DB:-dl_auto_pecas}; then
        log_success "PostgreSQL está saudável"
    else
        log_error "PostgreSQL não está respondendo"
        return 1
    fi
    
    # Verificar Redis
    if docker-compose -f docker-compose.vps.yml exec -T redis redis-cli ping | grep -q PONG; then
        log_success "Redis está saudável"
    else
        log_error "Redis não está respondendo"
        return 1
    fi
}

# Limpeza de recursos antigos
cleanup() {
    log "🧹 Limpando recursos antigos..."
    
    # Remover containers parados
    docker container prune -f
    
    # Remover imagens não utilizadas
    docker image prune -f
    
    # Remover volumes não utilizados
    docker volume prune -f
    
    # Limpar logs antigos
    find ./logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Limpeza concluída"
}

# Configurar SSL (se necessário)
setup_ssl() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log "🔒 Configurando SSL..."
        
        # Verificar se o domínio está configurado
        if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "seu-dominio.com" ]; then
            # Gerar certificado SSL se não existir
            if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
                log "Gerando certificado SSL para $DOMAIN..."
                certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m "$SSL_EMAIL" --redirect
            fi
            
            log_success "SSL configurado para $DOMAIN"
        else
            log_warning "Domínio não configurado, pulando SSL"
        fi
    fi
}

# Rollback em caso de falha
rollback() {
    log_error "Falha no deploy! Executando rollback..."
    
    # Restaurar backup do banco se existir
    if [ -f "$BACKUP_DIR/db_backup_$TIMESTAMP.sql" ]; then
        log "Restaurando backup do banco de dados..."
        docker-compose -f docker-compose.vps.yml exec -T postgres psql -U ${POSTGRES_USER:-dl_user} -d ${POSTGRES_DB:-dl_auto_pecas} < "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"
    fi
    
    # Reverter para versão anterior
    if [ -d ".git" ]; then
        git checkout HEAD~1
        docker-compose -f docker-compose.vps.yml up -d
    fi
    
    log_error "Rollback concluído"
}

# Função principal
main() {
    log "🚀 Iniciando deploy do DL SISTEMA"
    log "Ambiente: $ENVIRONMENT | Branch: $BRANCH"
    
    # Criar diretórios necessários
    mkdir -p logs/nginx logs/backend logs/frontend logs/worker logs/webhooks
    
    # Executar etapas do deploy
    check_requirements
    backup_database
    pull_updates
    build_images
    
    # Deploy com rollback automático em caso de falha
    if ! deploy_services; then
        rollback
        exit 1
    fi
    
    setup_ssl
    cleanup
    
    log_success "🎉 Deploy concluído com sucesso!"
    log "📊 Status dos serviços:"
    docker-compose -f docker-compose.vps.yml ps
    
    # Informações úteis
    echo ""
    echo "🔗 URLs do sistema:"
    echo "   Frontend: http://localhost"
    echo "   Backend API: http://localhost/api"
    echo "   Webhooks: http://localhost/webhooks"
    echo "   Health Check: http://localhost/health"
    echo ""
    echo "📋 Comandos úteis:"
    echo "   Ver logs: docker-compose -f docker-compose.vps.yml logs -f"
    echo "   Restart serviço: docker-compose -f docker-compose.vps.yml restart <servico>"
    echo "   Backup manual: $BACKUP_DIR/backup.sh"
    echo ""
}

# Tratamento de erros
trap 'log_error "Erro na linha $LINENO. Deploy falhou!"' ERR

# Executar deploy
main "$@"