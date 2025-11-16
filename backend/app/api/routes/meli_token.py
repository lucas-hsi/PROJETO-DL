from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.logger import logger
from app.services.mercadolivre_service import refresh_access_token, get_access_token, MeliAuthError
from app.services.token_monitor import token_monitor, start_token_monitor, stop_token_monitor

router = APIRouter(prefix="/api/meli", tags=["Mercado Livre - Token Management"])

class TokenStatus(BaseModel):
    access_token_valid: bool
    refresh_token_exists: bool
    monitor_running: bool
    last_refresh_attempt: Optional[str] = None
    message: str

class TokenRefreshResponse(BaseModel):
    success: bool
    message: str
    access_token_preview: Optional[str] = None
    refresh_token_preview: Optional[str] = None

@router.get("/token/status", response_model=TokenStatus)
def get_token_status():
    """
    Verifica o status atual dos tokens do Mercado Livre.
    """
    try:
        settings = get_settings()
        access_token = getattr(settings, "ML_ACCESS_TOKEN", "")
        refresh_token = getattr(settings, "ML_REFRESH_TOKEN", "")
        
        access_token_valid = False
        if access_token:
            try:
                # Testa se o access token é válido
                import requests
                r = requests.get(
                    f"{getattr(settings, 'ML_API_BASE_URL', 'https://api.mercadolibre.com')}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                access_token_valid = r.status_code == 200
            except Exception:
                access_token_valid = False
        
        return TokenStatus(
            access_token_valid=access_token_valid,
            refresh_token_exists=bool(refresh_token and not refresh_token.startswith("TG-")),
            monitor_running=token_monitor.running,
            message="Token status verificado com sucesso"
        )
        
    except Exception as e:
        logger.error({
            "event": "ML_TOKEN_STATUS_ERROR",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status do token: {str(e)}")

@router.post("/token/refresh", response_model=TokenRefreshResponse)
def refresh_token():
    """
    Força a renovação manual do token de acesso.
    """
    try:
        logger.info({"event": "ML_MANUAL_TOKEN_REFRESH_START"})
        
        access_token, refresh_token = refresh_access_token()
        
        if access_token:
            logger.info({"event": "ML_MANUAL_TOKEN_REFRESH_SUCCESS"})
            return TokenRefreshResponse(
                success=True,
                message="Token renovado com sucesso",
                access_token_preview=access_token[:6] + "***" if len(access_token) > 6 else "***",
                refresh_token_preview=refresh_token[:6] + "***" if refresh_token and len(refresh_token) > 6 else None
            )
        else:
            logger.error({"event": "ML_MANUAL_TOKEN_REFRESH_FAIL"})
            return TokenRefreshResponse(
                success=False,
                message="Falha ao renovar token. O refresh token pode estar expirado."
            )
            
    except MeliAuthError as e:
        logger.error({
            "event": "ML_MANUAL_TOKEN_REFRESH_AUTH_ERROR",
            "error": str(e)
        })
        
        if "invalid_grant" in str(e):
            return TokenRefreshResponse(
                success=False,
                message="Refresh token expirado. É necessário reautenticar com Mercado Livre. Acesse /api/meli/auth"
            )
        else:
            return TokenRefreshResponse(
                success=False,
                message=f"Erro de autenticação: {str(e)}"
            )
    except Exception as e:
        logger.error({
            "event": "ML_MANUAL_TOKEN_REFRESH_ERROR",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Erro ao renovar token: {str(e)}")

@router.post("/token/monitor/start")
def start_token_monitor_endpoint():
    """
    Inicia o monitoramento automático de tokens.
    """
    try:
        import asyncio
        # Como estamos em um contexto síncrono, precisamos criar um novo event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(start_token_monitor())
        loop.close()
        
        logger.info({"event": "ML_TOKEN_MONITOR_STARTED"})
        return {"message": "Monitoramento de tokens iniciado com sucesso"}
        
    except Exception as e:
        logger.error({
            "event": "ML_TOKEN_MONITOR_START_ERROR",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar monitoramento: {str(e)}")

@router.post("/token/monitor/stop")
def stop_token_monitor_endpoint():
    """
    Para o monitoramento automático de tokens.
    """
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(stop_token_monitor())
        loop.close()
        
        logger.info({"event": "ML_TOKEN_MONITOR_STOPPED"})
        return {"message": "Monitoramento de tokens parado com sucesso"}
        
    except Exception as e:
        logger.error({
            "event": "ML_TOKEN_MONITOR_STOP_ERROR",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Erro ao parar monitoramento: {str(e)}")

# Import necessário para evitar circular import
from app.core.config import get_settings