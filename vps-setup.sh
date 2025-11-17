#!/bin/bash

# 🚀 Script de Preparação VPS KingHost para DL_SISTEMA
# Executar como root ou com sudo

set -e

echo "🚀 Iniciando preparação da VPS KingHost para DL_SISTEMA..."

# Atualizar sistema
echo "📦 Atualizando sistema..."
apt update && apt upgrade -y

# Instalar dependências essenciais
echo "📦 Instalando dependências essenciais..."
apt install -y curl git ufw nginx software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Instalar Docker
echo "🐳 Instalando Docker..."
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Instalar Docker Compose
echo "🐳 Instalando Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Criar estrutura de pastas do projeto
echo "📁 Criando estrutura de pastas..."
mkdir -p /var/www/dl_sistema
mkdir -p /var/www/dl_sistema/logs
mkdir -p /var/www/dl_sistema/nginx/ssl
mkdir -p /var/www/dl_sistema/backup

# Configurar firewall
echo "🔥 Configurando firewall UFW..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https

# Configurar Nginx
echo "🌐 Configurando Nginx..."
systemctl enable nginx
systemctl start nginx

# Instalar Certbot para SSL
echo "🔒 Instalando Certbot para SSL..."
apt install -y certbot python3-certbot-nginx

# Criar usuário deploy (opcional, mas recomendado)
echo "👤 Criando usuário deploy..."
if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash deploy
    usermod -aG docker deploy
    echo "deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/local/bin/docker-compose, /bin/systemctl restart nginx" >> /etc/sudoers.d/deploy
fi

# Configurar limits para performance
echo "⚡ Configurando limits de sistema..."
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
echo "* soft nproc 32768" >> /etc/security/limits.conf
echo "* hard nproc 32768" >> /etc/security/limits.conf

# Configurar sysctl para performance
echo "⚡ Configurando sysctl..."
cat > /etc/sysctl.d/99-docker.conf << 'EOF'
# Docker performance tuning
net.core.somaxconn = 1024
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.ip_unprivileged_port_start = 80
EOF

sysctl -p /etc/sysctl.d/99-docker.conf

# Criar script de backup diário
echo "💾 Criando script de backup..."
cat > /var/www/dl_sistema/backup/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/www/dl_sistema/backup"

# Backup do banco de dados
docker exec dl_sistema_postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/db_backup_$DATE.sql

# Backup dos uploads/volumes
tar -czf $BACKUP_DIR/volumes_backup_$DATE.tar.gz /var/lib/docker/volumes/

# Remover backups antigos (manter últimos 7 dias)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
EOF

chmod +x /var/www/dl_sistema/backup/backup.sh

# Adicionar cron job para backup diário
(crontab -l 2>/dev/null; echo "0 3 * * * /var/www/dl_sistema/backup/backup.sh") | crontab -

# Criar logrotate para logs
echo "📋 Configurando logrotate..."
cat > /etc/logrotate.d/dl_sistema << 'EOF'
/var/www/dl_sistema/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

echo "✅ VPS KingHost preparada com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "1. Clonar o repositório: cd /var/www/dl_sistema && git clone <REPO>"
echo "2. Configurar .env com as variáveis corretas"
echo "3. Executar: docker-compose up -d"
echo "4. Configurar domínio e SSL"
echo ""
echo "🔧 Comandos úteis:"
echo "- Ver logs: docker-compose logs -f"
echo "- Restart serviços: docker-compose restart"
echo "- Backup manual: /var/www/dl_sistema/backup/backup.sh"
echo "- Status firewall: ufw status"
echo ""
echo "⚠️  IMPORTANTE: Faça logout e login novamente para aplicar grupo docker"