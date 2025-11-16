#!/usr/bin/env python3
"""
Agendador de Importações Automáticas
Script para executar importações via webhooks em horários específicos
"""
import asyncio
import aiohttp
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImportScheduler:
    """Agendador de importações automáticas"""
    
    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8000/api/webhooks/importacao")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "dl-auto-pecas-webhook-secret-2024")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        
    def generate_signature(self, payload: str) -> str:
        """Gera assinatura HMAC para webhook"""
        import hmac
        import hashlib
        
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def send_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Envia webhook para o backend"""
        try:
            payload_json = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(payload_json)
            
            headers = {
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "User-Agent": "DL-AutoPecas-Scheduler/1.0"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    data=payload_json,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutos timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Webhook {event_type} enviado com sucesso: {result}")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"❌ Erro no webhook {event_type}: {response.status} - {text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar webhook {event_type}: {e}")
            return False
    
    async def daily_import(self):
        """Importação diária - executa às 2h da manhã"""
        logger.info("🔄 Iniciando importação diária...")
        
        payload = {
            "event_type": "daily_import",
            "timestamp": datetime.utcnow().isoformat(),
            "dias": 7,  # Últimos 7 dias
            "limit": 5000
        }
        
        success = await self.send_webhook("daily_import", payload)
        
        if success:
            logger.info("✅ Importação diária concluída com sucesso")
        else:
            logger.error("❌ Importação diária falhou")
            
        return success
    
    async def incremental_import(self):
        """Importação incremental - a cada 6 horas"""
        logger.info("🔄 Iniciando importação incremental...")
        
        payload = {
            "event_type": "incremental_import",
            "timestamp": datetime.utcnow().isoformat(),
            "dias": 1,  # Último dia
            "limit": 2000
        }
        
        success = await self.send_webhook("incremental_import", payload)
        
        if success:
            logger.info("✅ Importação incremental concluída com sucesso")
        else:
            logger.error("❌ Importação incremental falhou")
            
        return success
    
    async def full_sync(self):
        """Sincronização completa semanal"""
        logger.info("🔄 Iniciando sincronização completa...")
        
        payload = {
            "event_type": "full_sync",
            "timestamp": datetime.utcnow().isoformat(),
            "limit": 25000  # Alto limite para sincronização completa
        }
        
        success = await self.send_webhook("full_sync", payload)
        
        if success:
            logger.info("✅ Sincronização completa concluída com sucesso")
        else:
            logger.error("❌ Sincronização completa falhou")
            
        return success
    
    async def test_webhook(self):
        """Testa o sistema de webhooks"""
        logger.info("🧪 Testando webhook...")
        
        # Testar endpoint de config
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/api/webhooks/importacao/config") as response:
                    if response.status == 200:
                        config = await response.json()
                        logger.info(f"✅ Config de webhook disponível: {config}")
                    else:
                        logger.warning(f"⚠️ Config não disponível: {response.status}")
        except Exception as e:
            logger.error(f"❌ Erro ao testar config: {e}")
        
        # Testar webhook de teste
        payload = {
            "event_type": "test_webhook",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Teste de sistema"
        }
        
        return await self.send_webhook("test_webhook", payload)

async def main():
    """Função principal do agendador"""
    scheduler = ImportScheduler()
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("Uso: python scheduler.py [comando]")
        print("Comandos disponíveis:")
        print("  test          - Testa o sistema de webhooks")
        print("  daily         - Executa importação diária")
        print("  incremental   - Executa importação incremental")
        print("  full-sync     - Executa sincronização completa")
        print("  schedule      - Executa agendamento completo (modo daemon)")
        return
    
    comando = sys.argv[1]
    
    if comando == "test":
        success = await scheduler.test_webhook()
        sys.exit(0 if success else 1)
        
    elif comando == "daily":
        success = await scheduler.daily_import()
        sys.exit(0 if success else 1)
        
    elif comando == "incremental":
        success = await scheduler.incremental_import()
        sys.exit(0 if success else 1)
        
    elif comando == "full-sync":
        success = await scheduler.full_sync()
        sys.exit(0 if success else 1)
        
    elif comando == "schedule":
        logger.info("🚀 Iniciando modo daemon de agendamento...")
        # Aqui implementaríamos o loop de agendamento com asyncio.schedule
        # Por enquanto, executamos uma vez de cada tipo
        
        logger.info("📅 Executando todas as tarefas de agendamento...")
        
        # Executar teste primeiro
        await scheduler.test_webhook()
        
        # Executar importações
        await asyncio.gather(
            scheduler.incremental_import(),
            scheduler.daily_import(),
            return_exceptions=True
        )
        
        logger.info("✅ Agendamento concluído")
        
    else:
        print(f"❌ Comando desconhecido: {comando}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())