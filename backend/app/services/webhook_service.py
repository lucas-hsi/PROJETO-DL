"""
Serviço de Webhooks para automatização de importações
"""
import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.core.config import get_settings
from app.models.webhook_log import WebhookLog
from app.services.mercadolivre_service import (
    importar_meli_todos_status_async,
    importar_meli_incremental_async
)

class WebhookService:
    """Serviço de webhooks para importação automática"""
    
    def __init__(self):
        self.settings = get_settings()
        self.webhook_secret = self.settings.WEBHOOK_SECRET or "dl-auto-pecas-webhook-secret-2024"
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verifica assinatura do webhook"""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Suporta formato 'sha256=' ou apenas hash
        if signature.startswith('sha256='):
            signature = signature[7:]
            
        return hmac.compare_digest(expected_signature, signature)
    
    async def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str], db: Session) -> Dict:
        """Processa webhook recebido"""
        try:
            # Verificar assinatura
            signature = headers.get('X-Hub-Signature-256') or headers.get('x-hub-signature-256')
            if signature:
                payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
                if not self.verify_signature(payload_bytes, signature):
                    return {"status": "error", "message": "Assinatura inválida"}
            
            # Identificar tipo de webhook
            event_type = payload.get('event_type', 'unknown')
            
            # Registrar webhook recebido
            webhook_log = WebhookLog(
                event_type=event_type,
                payload=payload,
                headers=headers,
                status="received"
            )
            db.add(webhook_log)
            db.commit()
            
            # Processar baseado no tipo
            result = await self.process_webhook_event(event_type, payload, db)
            
            # Atualizar log com resultado
            webhook_log.status = "completed" if result.get("success") else "failed"
            webhook_log.response = result
            db.commit()
            
            return result
            
        except Exception as e:
            logger.error({"event": "WEBHOOK_ERROR", "error": str(e)})
            return {"status": "error", "message": str(e)}
    
    async def process_webhook_event(self, event_type: str, payload: Dict, db: Session) -> Dict:
        """Processa evento específico do webhook"""
        
        if event_type == "daily_import":
            return await self.handle_daily_import(payload, db)
        elif event_type == "incremental_import":
            return await self.handle_incremental_import(payload, db)
        elif event_type == "full_sync":
            return await self.handle_full_sync(payload, db)
        elif event_type == "test_webhook":
            return await self.handle_test_webhook(payload, db)
        else:
            return {"status": "error", "message": f"Evento desconhecido: {event_type}"}
    
    async def handle_daily_import(self, payload: Dict, db: Session) -> Dict:
        """Processa importação diária automática"""
        try:
            logger.info({"event": "DAILY_IMPORT_START", "payload": payload})
            
            # Configurações da importação
            dias = payload.get('dias', 7)  # Padrão: últimos 7 dias
            limit = payload.get('limit', 5000)
            
            # Calcular data de início (dias atrás)
            from datetime import datetime, timedelta
            since_date = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3]
            
            # Executar importação incremental
            result = await importar_meli_incremental_async(since_date=since_date, hours=dias*24)
            
            # Registrar resultado
            logger.info({
                "event": "DAILY_IMPORT_COMPLETED",
                "importados": len(result[0]),
                "dias": dias,
                "limit": limit
            })
            
            return {
                "status": "success",
                "event": "daily_import",
                "importados": len(result[0]),
                "dias": dias,
                "message": f"Importação diária concluída: {len(result[0])} produtos"
            }
            
        except Exception as e:
            logger.error({"event": "DAILY_IMPORT_ERROR", "error": str(e)})
            return {"status": "error", "event": "daily_import", "error": str(e)}
    
    async def handle_incremental_import(self, payload: Dict, db: Session) -> Dict:
        """Processa importação incremental"""
        try:
            logger.info({"event": "INCREMENTAL_IMPORT_START"})
            
            dias = payload.get('dias', 1)  # Padrão: último dia
            limit = payload.get('limit', 2000)
            
            # Calcular data de início
            from datetime import datetime, timedelta
            since_date = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3]
            
            result = await importar_meli_incremental_async(since_date=since_date, hours=dias*24)
            
            logger.info({
                "event": "INCREMENTAL_IMPORT_COMPLETED",
                "importados": len(result[0])
            })
            
            return {
                "status": "success",
                "event": "incremental_import",
                "importados": len(result[0]),
                "message": f"Importação incremental concluída: {len(result[0])} produtos"
            }
            
        except Exception as e:
            logger.error({"event": "INCREMENTAL_IMPORT_ERROR", "error": str(e)})
            return {"status": "error", "event": "incremental_import", "error": str(e)}
    
    async def handle_full_sync(self, payload: Dict, db: Session) -> Dict:
        """Processa sincronização completa"""
        try:
            logger.info({"event": "FULL_SYNC_START"})
            
            limit = payload.get('limit', 20000)  # Alto limite para sincronização completa
            
            # Usar a função com paginação corrigida
            result = await importar_meli_todos_status_async(limit=limit)
            
            logger.info({
                "event": "FULL_SYNC_COMPLETED",
                "importados": len(result[0])
            })
            
            return {
                "status": "success",
                "event": "full_sync",
                "importados": len(result[0]),
                "message": f"Sincronização completa concluída: {len(result[0])} produtos"
            }
            
        except Exception as e:
            logger.error({"event": "FULL_SYNC_ERROR", "error": str(e)})
            return {"status": "error", "event": "full_sync", "error": str(e)}
    
    async def handle_test_webhook(self, payload: Dict, db: Session) -> Dict:
        """Processa webhook de teste"""
        return {
            "status": "success",
            "event": "test_webhook",
            "message": "Webhook funcionando corretamente",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_schedule_config(self) -> Dict:
        """Gera configuração de agendamento para o webhook"""
        return {
            "webhook_url": f"{self.settings.BACKEND_URL}/api/webhooks/importacao",
            "secret": self.webhook_secret,
            "schedules": [
                {
                    "name": "Importação Diária",
                    "cron": "0 2 * * *",  # 2h da manhã
                    "event_type": "daily_import",
                    "payload": {"dias": 7, "limit": 5000}
                },
                {
                    "name": "Importação Incremental",
                    "cron": "0 */6 * * *",  # A cada 6 horas
                    "event_type": "incremental_import", 
                    "payload": {"dias": 1, "limit": 2000}
                },
                {
                    "name": "Sincronização Completa Semanal",
                    "cron": "0 3 * * 0",  # Domingo 3h da manhã
                    "event_type": "full_sync",
                    "payload": {"limit": 25000}
                }
            ]
        }

# Instância global
webhook_service = WebhookService()