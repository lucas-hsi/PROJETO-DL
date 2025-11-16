"""
Rotas de Webhooks para importação automática
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json

from app.core.database import get_session
from app.core.logger import logger
from app.services.webhook_service import webhook_service
from app.core.config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/importacao")
async def webhook_importacao(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_session)
):
    """
    Endpoint para receber webhooks de importação automática
    
    Tipos de eventos:
    - daily_import: Importação diária (últimos 7 dias)
    - incremental_import: Importação incremental (último dia)
    - full_sync: Sincronização completa (todos os produtos)
    - test_webhook: Teste de webhook
    """
    try:
        # Ler payload bruto
        raw_body = await request.body()
        
        # Parse JSON
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON inválido")
        
        # Headers para verificação
        headers = dict(request.headers)
        if x_hub_signature_256:
            headers['x-hub-signature-256'] = x_hub_signature_256
        
        logger.info({
            "event": "WEBHOOK_RECEIVED",
            "event_type": payload.get('event_type'),
            "headers": {k: v for k, v in headers.items() if k.lower().startswith('x-')}
        })
        
        # Processar webhook de forma assíncrona
        result = await webhook_service.handle_webhook(payload, headers, db)
        
        # Se for um evento grande, podemos processar em background
        if payload.get('event_type') in ['full_sync', 'daily_import']:
            # Já processamos sincronamente por enquanto
            pass
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error({"event": "WEBHOOK_PROCESSING_ERROR", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erro ao processar webhook: {str(e)}")

@router.get("/importacao/config")
async def get_webhook_config():
    """Retorna configuração de webhooks para setup externo"""
    try:
        config = webhook_service.generate_schedule_config()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        logger.error({"event": "WEBHOOK_CONFIG_ERROR", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erro ao gerar config: {str(e)}")

@router.post("/importacao/test")
async def test_webhook(
    request: Request,
    db: Session = Depends(get_session)
):
    """Endpoint para testar webhooks"""
    try:
        # Testar com evento de teste
        test_payload = {
            "event_type": "test_webhook",
            "timestamp": "2024-01-01T00:00:00Z",
            "message": "Teste de webhook"
        }
        
        headers = dict(request.headers)
        result = await webhook_service.handle_webhook(test_payload, headers, db)
        
        return {
            "status": "success",
            "test_result": result,
            "message": "Webhook testado com sucesso"
        }
        
    except Exception as e:
        logger.error({"event": "WEBHOOK_TEST_ERROR", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erro ao testar webhook: {str(e)}")

@router.get("/importacao/logs")
async def get_webhook_logs(
    limit: int = 50,
    event_type: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Retorna logs de webhooks"""
    try:
        from app.models.webhook_log import WebhookLog
        
        query = db.query(WebhookLog).order_by(WebhookLog.created_at.desc())
        
        if event_type:
            query = query.filter(WebhookLog.event_type == event_type)
        
        logs = query.limit(limit).all()
        
        return {
            "status": "success",
            "logs": [log.to_dict() for log in logs],
            "total": len(logs)
        }
        
    except Exception as e:
        logger.error({"event": "WEBHOOK_LOGS_ERROR", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Erro ao buscar logs: {str(e)}")