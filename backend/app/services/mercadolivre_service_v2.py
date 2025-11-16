"""
Serviço de integração com Mercado Livre usando novo sistema de tokens permanentes
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import random

import requests
import aiohttp
from app.core.config import get_settings
from app.core.logger import logger
from app.models.ml_log import MLLog
from app.core.database import get_session
from app.services.meli_hash_utils import compute_meli_item_hash
from app.services.ml_token_manager import (
    ml_token_manager, 
    get_ml_token, 
    check_ml_token_status,
    notify_ml_token_renewal
)
from app.repositories.meli_item_snapshot_repo import (
    get_snapshot_by_meli_id,
    get_snapshot_by_sku,
    upsert_snapshot_new,
    mark_snapshot_unchanged,
    update_snapshot_changed,
)

_tg_exchange_lock = threading.Lock()


class MeliAuthError(Exception):
    """Custom exception for Mercado Libre authentication errors"""
    
    def __init__(self, status_code: int, url: str, message: str):
        self.status_code = status_code
        self.url = url
        self.message = message
        super().__init__(f"ML auth error {status_code} at {url}: {message}")


def retry_with_backoff(func, max_retries=3, base_delay=1, max_delay=60):
    """
    Retry function with exponential backoff and jitter.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Function result or raises last exception
    """
    for attempt in range(max_retries):
        try:
            return func()
        except MeliAuthError as e:
            if attempt == max_retries - 1:
                logger.error({
                    "event": "ML_RETRY_EXHAUSTED",
                    "error": str(e),
                    "attempts": max_retries
                })
                raise
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            
            logger.warning({
                "event": "ML_RETRY_ATTEMPT",
                "attempt": attempt + 1,
                "max_retries": max_retries,
                "delay": delay,
                "error": str(e)
            })
            
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error({
                    "event": "ML_RETRY_EXHAUSTED_GENERIC",
                    "error": str(e),
                    "attempts": max_retries
                })
                raise
            
            # Generic retry with shorter delay
            delay = min(base_delay * (2 ** attempt), max_delay // 2)
            
            logger.warning({
                "event": "ML_RETRY_ATTEMPT_GENERIC",
                "attempt": attempt + 1,
                "max_retries": max_retries,
                "delay": delay,
                "error": str(e)
            })
            
            time.sleep(delay)


def get_access_token(operation_type: str = "read") -> str:
    """
    Obtém o token de acesso usando o novo sistema permanente.
    
    Args:
        operation_type: "read" para leitura, "write" para escrita
    
    Returns:
        Token válido para a operação
    """
    # Verificar status dos tokens
    token_status = check_ml_token_status()
    
    # Notificar se renovação está próxima
    if token_status.get("needs_renewal"):
        notify_ml_token_renewal()
    
    def _get_token_internal():
        # Usar novo sistema de tokens
        token = get_ml_token(operation_type)
        
        if not token:
            # Se não conseguiu token, tentar client credentials
            if operation_type == "read":
                logger.warning({
                    "event": "ML_FALLBACK_TO_CLIENT_CREDENTIALS",
                    "message": "Usando Client Credentials como fallback"
                })
                token = ml_token_manager.get_client_credentials_token()
            
            if not token:
                raise MeliAuthError(401, "api.mercadolibre.com/oauth/token", "Nenhum token válido disponível")
        
        # Testar token
        try:
            test_response = requests.get(
                "https://api.mercadolibre.com/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            
            if test_response.status_code == 401:
                logger.error({
                    "event": "ML_TOKEN_TEST_FAILED",
                    "operation_type": operation_type,
                    "status": test_response.status_code
                })
                raise MeliAuthError(401, "api.mercadolibre.com/users/me", "Token inválido ou expirado")
            
            logger.info({
                "event": "ML_ACCESS_TOKEN_VALID",
                "operation_type": operation_type,
                "status": "sucesso",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return token
            
        except requests.RequestException as e:
            logger.error({
                "event": "ML_TOKEN_TEST_ERROR",
                "error": str(e),
                "operation_type": operation_type
            })
            raise MeliAuthError(500, "api.mercadolibre.com/users/me", f"Erro ao testar token: {e}")
    
    # Usar retry com backoff
    return retry_with_backoff(_get_token_internal, max_retries=5, base_delay=2, max_delay=120)


def refresh_access_token():
    """
    Renova o access token usando o refresh token (Authorization Code)
    """
    settings = get_settings()
    refresh_token = getattr(settings, "ML_REFRESH_TOKEN", "")
    
    if not refresh_token:
        logger.error({
            "event": "ML_NO_REFRESH_TOKEN",
            "message": "Nenhum refresh token disponível para renovação"
        })
        return None, None
    
    try:
        logger.info({
            "event": "ML_REFRESH_TOKEN_ATTEMPT",
            "url": "https://api.mercadolibre.com/oauth/token",
            "refresh_token_preview": refresh_token[:10] + "..."
        })
        
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.MERCADO_LIVRE_CLIENT_ID,
                "client_secret": settings.MERCADO_LIVRE_CLIENT_SECRET,
                "refresh_token": refresh_token
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", refresh_token)  # Mantém o mesmo se não vier novo
            
            logger.info({
                "event": "ML_REFRESH_TOKEN_SUCCESS",
                "new_access_token_preview": new_access_token[:10] + "..."
            })
            
            # Atualizar configurações
            setattr(settings, "ML_ACCESS_TOKEN", new_access_token)
            if new_refresh_token != refresh_token:
                setattr(settings, "ML_REFRESH_TOKEN", new_refresh_token)
            
            return new_access_token, new_refresh_token
        else:
            error_data = response.json() if response.text else {}
            logger.error({
                "event": "IMPORT_MELI_TOKEN_REFRESH_FAIL",
                "status": response.status_code,
                "url": "https://api.mercadolibre.com/oauth/token",
                "body": error_data
            })
            
            if response.status_code == 400:
                logger.error({
                    "event": "ML_INVALID_GRANT_ERROR",
                    "message": "Refresh token inválido ou expirado. Necessário reautenticação.",
                    "body": error_data
                })
            
            return None, None
            
    except Exception as e:
        logger.error({
            "event": "ML_REFRESH_TOKEN_ERROR",
            "error": str(e)
        })
        return None, None


def get_user_items(access_token: str, limit: int = 50, offset: int = 0, since: Optional[datetime] = None) -> Dict:
    """
    Busca itens do usuário logado
    """
    params = {
        "limit": min(limit, 50),
        "offset": offset,
        "sort": "date_created_desc"
    }
    
    if since:
        params["since"] = since.isoformat() + "Z"
    
    try:
        response = requests.get(
            "https://api.mercadolibre.com/users/me/items/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        logger.error({
            "event": "ML_GET_USER_ITEMS_ERROR",
            "error": str(e),
            "limit": limit,
            "offset": offset
        })
        raise


def get_item_details(access_token: str, item_id: str) -> Dict:
    """
    Obtém detalhes de um item específico
    """
    try:
        response = requests.get(
            f"https://api.mercadolibre.com/items/{item_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"include_attributes": "all"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        logger.error({
            "event": "ML_GET_ITEM_DETAILS_ERROR",
            "error": str(e),
            "item_id": item_id
        })
        raise


def import_user_items(limit: int = 1000, since_hours: int = 24) -> Dict:
    """
    Importa itens do usuário usando o novo sistema de tokens
    """
    logger.info({
        "event": "IMPORT_MELI_START",
        "limit": limit,
        "since_hours": since_hours
    })
    
    try:
        # Obter token para leitura (usa Client Credentials se possível)
        access_token = get_access_token("read")
        
        if not access_token:
            raise Exception("Não foi possível obter token válido para importação")
        
        # Calcular data de corte
        since = datetime.utcnow() - timedelta(hours=since_hours) if since_hours > 0 else None
        
        # Buscar itens
        all_items = []
        offset = 0
        
        while offset < limit:
            batch_size = min(50, limit - offset)
            
            logger.info({
                "event": "IMPORT_MELI_BATCH",
                "offset": offset,
                "limit": batch_size
            })
            
            try:
                result = get_user_items(access_token, batch_size, offset, since)
                items = result.get("results", [])
                
                if not items:
                    logger.info({
                        "event": "IMPORT_MELI_NO_MORE_ITEMS",
                        "offset": offset
                    })
                    break
                
                # Processar cada item
                for item_id in items:
                    try:
                        item_details = get_item_details(access_token, item_id)
                        
                        # Aqui você processaria o item (salvar no banco, etc.)
                        all_items.append(item_details)
                        
                        logger.info({
                            "event": "IMPORT_MELI_ITEM_SUCCESS",
                            "item_id": item_id,
                            "title": item_details.get("title", "")[:50]
                        })
                        
                    except Exception as e:
                        logger.error({
                            "event": "IMPORT_MELI_ITEM_ERROR",
                            "item_id": item_id,
                            "error": str(e)
                        })
                
                offset += batch_size
                
                # Pequena pausa para não sobrecarregar a API
                time.sleep(0.5)
                
            except Exception as e:
                logger.error({
                    "event": "IMPORT_MELI_BATCH_ERROR",
                    "offset": offset,
                    "error": str(e)
                })
                break
        
        logger.info({
            "event": "IMPORT_MELI_COMPLETE",
            "total_items": len(all_items),
            "limit": limit
        })
        
        return {
            "success": True,
            "items_imported": len(all_items),
            "items": all_items
        }
        
    except Exception as e:
        logger.error({
            "event": "IMPORT_MELI_ERROR",
            "error": str(e)
        })
        return {
            "success": False,
            "error": str(e),
            "items_imported": 0,
            "items": []
        }


# Funções auxiliares para manter compatibilidade
def get_user_items_with_retry(limit: int = 50, offset: int = 0, since: Optional[datetime] = None) -> Dict:
    """
    Wrapper para manter compatibilidade com código existente
    """
    access_token = get_access_token("read")
    return get_user_items(access_token, limit, offset, since)


def get_item_details_with_retry(item_id: str) -> Dict:
    """
    Wrapper para manter compatibilidade com código existente
    """
    access_token = get_access_token("read")
    return get_item_details(access_token, item_id)