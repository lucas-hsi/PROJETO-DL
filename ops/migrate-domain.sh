#!/bin/bash
set -e

echo "[1/4] Aplicando Virtual Host..."
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf
sudo rm -f /etc/nginx/sites-enabled/sistemadl.conf || true

echo "[2/4] Testando Nginx..."
sudo nginx -t

echo "[3/4] Reload Nginx..."
sudo systemctl reload nginx

echo "[4/4] Rebuild Frontend..."
docker compose -f docker-compose.vps.yml up -d --build frontend

echo "Migração aplicada com sucesso!"