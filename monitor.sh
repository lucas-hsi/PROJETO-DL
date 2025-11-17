#!/bin/bash

# 📊 DL SISTEMA - Monitoramento e Manutenção
# Script completo para monitoramento, limpeza e manutenção do sistema

set -e

# Configurações
PROJECT_DIR="/var/www/dl_sistema"
LOG_DIR="$PROJECT_DIR/logs"
BACKUP_DIR="$PROJECT_DIR/backup"
DISK_THRESHOLD=85
MEMORY_THRESHOLD=90
CPU_THRESHOLD=80

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
}

# Verificar saúde dos containers
check_containers() {
    log "🐳 Verificando containers Docker..."
    
    # Lista de containers esperados
    CONTAINERS=("dl_sistema_postgres" "dl_sistema_redis" "dl_sistema_backend" "dl_sistema_worker" "dl_sistema_webhooks" "dl_sistema_frontend" "dl_sistema_nginx")
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
            
            if [ "$STATUS" = "running" ]; then
                if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "none" ]; then
                    log_success "$container: $STATUS ($HEALTH)"
                else
                    log_warning "$container: $STATUS ($HEALTH)"
                fi
            else
                log_error "$container: $STATUS"
            fi
        else
            log_error "$container: não encontrado"
        fi
    done
}

# Verificar recursos do sistema
check_system_resources() {
    log "💻 Verificando recursos do sistema..."
    
    # Uso de disco
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        log_error "Uso de disco alto: ${DISK_USAGE}%"
    else
        log_success "Uso de disco: ${DISK_USAGE}%"
    fi
    
    # Uso de memória
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$MEMORY_USAGE" -gt "$MEMORY_THRESHOLD" ]; then
        log_error "Uso de memória alto: ${MEMORY_USAGE}%"
    else
        log_success "Uso de memória: ${MEMORY_USAGE}%"
    fi
    
    # Uso de CPU
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}' | cut -d'.' -f1)
    if [ "$CPU_USAGE" -gt "$CPU_THRESHOLD" ]; then
        log_error "Uso de CPU alto: ${CPU_USAGE}%"
    else
        log_success "Uso de CPU: ${CPU_USAGE}%"
    fi
    
    # Carga do sistema
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    log "Carga média do sistema: $LOAD_AVG"
}

# Verificar portas e conectividade
check_connectivity() {
    log "🔗 Verificando conectividade..."
    
    # Portas principais
    PORTS=(80 443 8000 8080 5432 6379)
    
    for port in "${PORTS[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            log_success "Porta $port: aberta"
        else
            log_warning "Porta $port: fechada"
        fi
    done
    
    # Testar endpoints principais
    ENDPOINTS=("http://localhost/health" "http://localhost:8000/healthz" "http://localhost:8080/healthz")
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log_success "Endpoint $endpoint: respondendo"
        else
            log_error "Endpoint $endpoint: não respondendo"
        fi
    done
}

# Verificar logs de erro
check_logs() {
    log "📋 Verificando logs de erro..."
    
    # Verificar logs recentes por erros
    ERROR_COUNT=0
    
    # Backend logs
    if [ -f "$LOG_DIR/backend.log" ]; then
        BACKEND_ERRORS=$(tail -n 100 "$LOG_DIR/backend.log" | grep -i "error\|exception\|traceback" | wc -l)
        if [ "$BACKEND_ERRORS" -gt 0 ]; then
            log_warning "Backend: $BACKEND_ERRORS erros recentes"
            ERROR_COUNT=$((ERROR_COUNT + BACKEND_ERRORS))
        fi
    fi
    
    # Worker logs
    if [ -f "$LOG_DIR/worker.log" ]; then
        WORKER_ERRORS=$(tail -n 100 "$LOG_DIR/worker.log" | grep -i "error\|exception\|traceback" | wc -l)
        if [ "$WORKER_ERRORS" -gt 0 ]; then
            log_warning "Worker: $WORKER_ERRORS erros recentes"
            ERROR_COUNT=$((ERROR_COUNT + WORKER_ERRORS))
        fi
    fi
    
    # Webhooks logs
    if [ -f "$LOG_DIR/webhooks.log" ]; then
        WEBHOOK_ERRORS=$(tail -n 100 "$LOG_DIR/webhooks.log" | grep -i "error\|exception\|traceback" | wc -l)
        if [ "$WEBHOOK_ERRORS" -gt 0 ]; then
            log_warning "Webhooks: $WEBHOOK_ERRORS erros recentes"
            ERROR_COUNT=$((ERROR_COUNT + WEBHOOK_ERRORS))
        fi
    fi
    
    if [ "$ERROR_COUNT" -eq 0 ]; then
        log_success "Nenhum erro encontrado nos logs recentes"
    else
        log_warning "Total de erros encontrados: $ERROR_COUNT"
    fi
}

# Limpeza de logs e recursos
cleanup() {
    log "🧹 Executando limpeza de recursos..."
    
    # Limpar logs antigos (manter últimos 7 dias)
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
    
    # Limpar backups antigos (manter últimos 30 dias)
    find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null || true
    
    # Limpar Docker
    docker system prune -f --volumes
    
    # Limpar cache e arquivos temporários
    rm -rf /tmp/* 2>/dev/null || true
    
    log_success "Limpeza concluída"
}

# Backup rápido
quick_backup() {
    log "💾 Executando backup rápido..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/quick_backup_$TIMESTAMP"
    
    # Backup do banco de dados
    if docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" ps postgres | grep -q "Up"; then
        docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" exec -T postgres pg_dump -U dl_user dl_auto_pecas > "$BACKUP_FILE.sql"
        log_success "Backup do banco criado: $BACKUP_FILE.sql"
    fi
    
    # Backup dos volumes Docker
    tar -czf "$BACKUP_FILE.volumes.tar.gz" /var/lib/docker/volumes/ 2>/dev/null || true
    
    log_success "Backup rápido concluído"
}

# Verificar SSL
check_ssl() {
    log "🔒 Verificando certificado SSL..."
    
    DOMAIN=$(grep "DOMAIN=" "$PROJECT_DIR/.env" | cut -d'=' -f2 | head -n1)
    
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "seu-dominio.com" ]; then
        if [ -f "$PROJECT_DIR/check_ssl.sh" ]; then
            "$PROJECT_DIR/check_ssl.sh"
        else
            # Verificação básica
            EXPIRY=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
            if [ -n "$EXPIRY" ]; then
                EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
                CURRENT_EPOCH=$(date +%s)
                DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
                
                if [ "$DAYS_LEFT" -lt 30 ]; then
                    log_warning "SSL expira em $DAYS_LEFT dias!"
                else
                    log_success "SSL válido por $DAYS_LEFT dias"
                fi
            else
                log_error "Não foi possível verificar o SSL"
            fi
        fi
    else
        log_warning "Domínio não configurado, pulando verificação SSL"
    fi
}

# Relatório completo
generate_report() {
    log "📊 Gerando relatório de saúde..."
    
    REPORT_FILE="$LOG_DIR/health_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================="
        echo "📊 RELATÓRIO DE SAÚDE - DL SISTEMA"
        echo "========================================="
        echo "Data: $(date)"
        echo "Servidor: $(hostname)"
        echo ""
        echo "🐳 CONTAINERS:"
        docker-compose -f "$PROJECT_DIR/docker-compose.vps.yml" ps
        echo ""
        echo "💻 RECURSOS DO SISTEMA:"
        echo "Uso de disco: $(df / | tail -1 | awk '{print $5}')"
        echo "Uso de memória: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%"
        echo "Carga média: $(uptime | awk -F'load average:' '{print $2}')"
        echo ""
        echo "🔗 PORTAS:"
        netstat -tuln | grep -E ":(80|443|8000|8080|5432|6379)"
        echo ""
        echo "📋 ÚLTIMOS LOGS DE ERRO:"
        tail -n 20 "$LOG_DIR/backend.log" 2>/dev/null | grep -i "error\|exception" || echo "Sem erros recentes"
        echo ""
        echo "🔒 SSL:"
        check_ssl 2>/dev/null || echo "SSL não configurado"
        echo ""
        echo "========================================="
    } > "$REPORT_FILE"
    
    log_success "Relatório gerado: $REPORT_FILE"
}

# Função principal
main() {
    log "📊 Iniciando monitoramento do DL SISTEMA"
    
    case "${1:-full}" in
        "containers")
            check_containers
            ;;
        "system")
            check_system_resources
            ;;
        "connectivity")
            check_connectivity
            ;;
        "logs")
            check_logs
            ;;
        "cleanup")
            cleanup
            ;;
        "backup")
            quick_backup
            ;;
        "ssl")
            check_ssl
            ;;
        "report")
            generate_report
            ;;
        "full"|"")
            check_containers
            check_system_resources
            check_connectivity
            check_logs
            check_ssl
            generate_report
            ;;
        *)
            echo "Uso: $0 [containers|system|connectivity|logs|cleanup|backup|ssl|report|full]"
            echo ""
            echo "Opções:"
            echo "  containers   - Verificar status dos containers"
            echo "  system       - Verificar recursos do sistema"
            echo "  connectivity - Verificar conectividade e portas"
            echo "  logs         - Verificar logs de erro"
            echo "  cleanup      - Executar limpeza de recursos"
            echo "  backup       - Executar backup rápido"
            echo "  ssl          - Verificar certificado SSL"
            echo "  report       - Gerar relatório completo"
            echo "  full         - Executar todas as verificações (padrão)"
            exit 1
            ;;
    esac
    
    log_success "Monitoramento concluído!"
}

# Tratamento de erros
trap 'log_error "Erro na linha $LINENO. Monitoramento falhou!"' ERR

# Executar monitoramento
main "$@"