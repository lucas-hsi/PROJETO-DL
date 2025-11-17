#!/bin/bash

# 🔒 SSL Setup Script for DL SISTEMA
# Automatiza a configuração de SSL com Let's Encrypt

set -e

# Configurações
DOMAIN=${1:-seu-dominio.com}
EMAIL=${2:-admin@$DOMAIN}
NGINX_CONF_DIR="/etc/nginx/conf.d"
PROJECT_DIR="/var/www/dl_sistema"

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

# Verificar se o domínio está configurado
check_domain() {
    log "🔍 Verificando configuração do domínio..."
    
    if [ "$DOMAIN" = "seu-dominio.com" ]; then
        log_error "Domínio não configurado! Edite o arquivo .env e configure DOMAIN"
        exit 1
    fi
    
    # Verificar se o domínio resolve para este servidor
    SERVER_IP=$(curl -s http://checkip.amazonaws.com)
    DOMAIN_IP=$(dig +short $DOMAIN @8.8.8.8 | head -n1)
    
    if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
        log_warning "O domínio $DOMAIN não aponta para este servidor ($SERVER_IP != $DOMAIN_IP)"
        log_warning "Certifique-se de que o DNS está configurado corretamente"
        read -p "Continuar mesmo assim? (s/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Domínio verificado: $DOMAIN"
}

# Instalar Certbot se necessário
install_certbot() {
    log "📦 Verificando Certbot..."
    
    if ! command -v certbot &> /dev/null; then
        log "Instalando Certbot..."
        apt update
        apt install -y certbot python3-certbot-nginx
    fi
    
    log_success "Certbot está instalado"
}

# Criar configuração Nginx temporária para validação
create_temp_nginx_config() {
    log "🌐 Criando configuração Nginx temporária..."
    
    cat > $NGINX_CONF_DIR/dl_sistema_temp.conf << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF
    
    # Criar diretório para desafios ACME
    mkdir -p /var/www/certbot
    
    # Testar e recarregar Nginx
    nginx -t && systemctl reload nginx
    
    log_success "Configuração temporária criada"
}

# Gerar certificado SSL
generate_ssl() {
    log "🔒 Gerando certificado SSL para $DOMAIN..."
    
    # Remover certificado existente se houver
    if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        log_warning "Certificado existente encontrado, removendo..."
        certbot delete --cert-name $DOMAIN --non-interactive
    fi
    
    # Gerar novo certificado
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --non-interactive
    
    if [ $? -eq 0 ]; then
        log_success "Certificado SSL gerado com sucesso!"
    else
        log_error "Falha ao gerar certificado SSL"
        exit 1
    fi
}

# Configurar renovação automática
setup_auto_renewal() {
    log "🔄 Configurando renovação automática..."
    
    # Testar renovação
    certbot renew --dry-run
    
    if [ $? -eq 0 ]; then
        log_success "Teste de renovação passou"
    else
        log_warning "Teste de renovação falhou, mas o certificado foi gerado"
    fi
    
    # Adicionar cron job para renovação
    (crontab -l 2>/dev/null; echo "0 2 * * * certbot renew --quiet && systemctl reload nginx") | crontab -
    
    log_success "Renovação automática configurada"
}

# Atualizar configuração Nginx com SSL
update_nginx_ssl() {
    log "🌐 Atualizando configuração Nginx com SSL..."
    
    # Copiar configuração SSL do projeto
    if [ -f "$PROJECT_DIR/nginx/nginx.vps.conf" ]; then
        cp "$PROJECT_DIR/nginx/nginx.vps.conf" "$NGINX_CONF_DIR/dl_sistema.conf"
        
        # Substituir placeholders
        sed -i "s/seu-dominio.com/$DOMAIN/g" "$NGINX_CONF_DIR/dl_sistema.conf"
        sed -i "s|ssl_certificate /etc/nginx/ssl/cert.pem;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" "$NGINX_CONF_DIR/dl_sistema.conf"
        sed -i "s|ssl_certificate_key /etc/nginx/ssl/key.pem;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" "$NGINX_CONF_DIR/dl_sistema.conf"
        
        # Remover configuração temporária
        rm -f "$NGINX_CONF_DIR/dl_sistema_temp.conf"
        
        # Testar e recarregar Nginx
        nginx -t && systemctl reload nginx
        
        log_success "Configuração Nginx atualizada com SSL"
    else
        log_error "Arquivo nginx.vps.conf não encontrado em $PROJECT_DIR/nginx/"
        exit 1
    fi
}

# Testar configuração SSL
test_ssl() {
    log "🧪 Testando configuração SSL..."
    
    # Testar conexão HTTPS
    if curl -f -s https://$DOMAIN > /dev/null; then
        log_success "Conexão HTTPS funcionando!"
    else
        log_warning "Conexão HTTPS falhou, mas o certificado foi instalado"
    fi
    
    # Verificar validade do certificado
    echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates
    
    log_success "Configuração SSL testada"
}

# Criar script de verificação de SSL
create_ssl_check_script() {
    log "📋 Criando script de verificação de SSL..."
    
    cat > "$PROJECT_DIR/check_ssl.sh" << 'EOF'
#!/bin/bash

# Verificar validade do certificado SSL
DOMAIN=$(grep "DOMAIN=" /var/www/dl_sistema/.env | cut -d'=' -f2)

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "seu-dominio.com" ]; then
    echo "Domínio não configurado"
    exit 1
fi

echo "Verificando certificado SSL para $DOMAIN..."

echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates

# Verificar dias até expiração
EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

echo "Dias até expiração: $DAYS_LEFT"

if [ "$DAYS_LEFT" -lt 30 ]; then
    echo "⚠️  Atenção: Certificado expira em $DAYS_LEFT dias!"
    exit 1
else
    echo "✅ Certificado válido por $DAYS_LEFT dias"
fi
EOF
    
    chmod +x "$PROJECT_DIR/check_ssl.sh"
    log_success "Script de verificação criado"
}

# Função principal
main() {
    log "🔒 Iniciando configuração SSL para $DOMAIN"
    
    check_domain
    install_certbot
    create_temp_nginx_config
    generate_ssl
    setup_auto_renewal
    update_nginx_ssl
    test_ssl
    create_ssl_check_script
    
    log_success "🎉 Configuração SSL concluída com sucesso!"
    echo ""
    echo "🔗 URLs para teste:"
    echo "   https://$DOMAIN"
    echo "   https://www.$DOMAIN"
    echo ""
    echo "📋 Comandos úteis:"
    echo "   Verificar SSL: $PROJECT_DIR/check_ssl.sh"
    echo "   Renovar manual: certbot renew"
    echo "   Testar renovação: certbot renew --dry-run"
    echo ""
    echo "⚠️  Importante:"
    echo "   - O certificado será renovado automaticamente"
    echo "   - Monitore os logs de renovação em /var/log/letsencrypt/"
    echo "   - Configure alertas para expiração do certificado"
}

# Tratamento de erros
trap 'log_error "Erro na linha $LINENO. SSL setup falhou!"' ERR

# Executar script
main "$@"