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
from app.core.database import get_session, engine
from sqlmodel import Session, select
from app.models.ml_token import MlToken
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
        operation_type: "read" para leitura (usa Client Credentials), "write" para escrita
    
    Returns:
        Token válido para a operação
    """
    # Verificar status dos tokens
    token_status = check_ml_token_status()
    
    # Notificar se renovação está próxima
    if token_status.get("needs_renewal"):
        notify_ml_token_renewal()
    
    def _get_token_internal():
        try:
            token = None
            if operation_type == "read":
                token = ml_token_manager.get_client_credentials_token()
            else:
                with Session(engine) as s:
                    row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
                if row and row.access_token:
                    token = row.access_token
                else:
                    access, _ = refresh_access_token()
                    if access:
                        with Session(engine) as s:
                            row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
                        token = (row.access_token if row else access)
            
            if not token:
                # Se não conseguiu token, tentar client credentials
                if operation_type == "read":
                    logger.warning({
                        "event": "ML_FALLBACK_TO_CLIENT_CREDENTIALS",
                        "message": "Usando Client Credentials como fallback para leitura"
                    })
                    token = ml_token_manager.get_client_credentials_token()
                
                if not token:
                    raise MeliAuthError(401, "api.mercadolibre.com/oauth/token", "Nenhum token válido disponível")
            
            # Testar token (apenas para Authorization Code, não para Client Credentials)
            if operation_type == "write":
                # Para operações de escrita, testar com endpoint que requer Authorization Code
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
                    
                except requests.exceptions.RequestException as e:
                    logger.error({
                        "event": "ML_TOKEN_TEST_ERROR",
                        "operation_type": operation_type,
                        "error": str(e)
                    })
                    raise MeliAuthError(500, "api.mercadolibre.com/users/me", f"Erro ao testar token: {e}")
            else:
                logger.info({"event": "ML_ACCESS_TOKEN_VALID", "operation_type": operation_type, "token_type": "client_credentials", "status": "sucesso", "timestamp": datetime.utcnow().isoformat()})
            
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


class MeliAuthError(Exception):
    def __init__(self, status: int, endpoint: str, body: str):
        self.status = status
        self.endpoint = endpoint
        self.body = body
        super().__init__(f"ML auth error {status} at {endpoint}")


def load_tokens_from_db() -> MlToken | None:
    with Session(engine) as s:
        return s.exec(select(MlToken).where(MlToken.id == 1)).first()


def save_tokens_to_db(access_token: str | None, refresh_token: str | None, expires_in: int | None, token_type: str | None, scope: str | None, user_id: str | None) -> None:
    now = datetime.utcnow()
    with Session(engine) as s:
        row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
        if row is None:
            row = MlToken(id=1)
        if access_token is not None:
            row.access_token = access_token
        if refresh_token is not None:
            row.refresh_token = refresh_token
        row.expires_in = expires_in
        row.token_type = token_type
        row.scope = scope
        row.user_id = user_id
        row.updated_at = now
        if row.created_at is None:
            row.created_at = now
        s.add(row)
        s.commit()


def is_expired(row: MlToken | None) -> bool:
    if row is None:
        return True
    if row.expires_in is None or row.updated_at is None:
        return True
    margin = 300
    return datetime.utcnow() >= row.updated_at + timedelta(seconds=int(row.expires_in or 0) - margin)


def refresh_access_token() -> tuple[str | None, str | None]:
    """
    Renova o token de acesso usando o refresh token, com retry automático.
    """
    settings = get_settings()
    
    def _refresh_token_internal() -> tuple[str | None, str | None]:
        url = f"{settings.ML_API_BASE_URL}/oauth/token"
        with Session(engine) as s:
            row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
        refresh_val = row.refresh_token if row else None
        if not refresh_val:
            logger.error({"event": "ML_REFRESH_TOKEN_MISSING"})
            return None, None
        
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.ML_CLIENT_ID,
            "client_secret": settings.ML_CLIENT_SECRET,
            "refresh_token": refresh_val,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            logger.info({
                "event": "ML_REFRESH_TOKEN_ATTEMPT",
                "url": url,
                "refresh_token_preview": settings.ML_REFRESH_TOKEN[:10] + "..." if len(settings.ML_REFRESH_TOKEN) > 10 else settings.ML_REFRESH_TOKEN
            })
            
            resp = requests.post(url, data=payload, headers=headers, timeout=30)
            status_code = resp.status_code
            
            body = {}
            try:
                body = resp.json()
            except ValueError:
                body = {"raw": resp.text}
                
            if status_code >= 400:
                logger.error({
                    "event": "IMPORT_MELI_TOKEN_REFRESH_FAIL",
                    "status": status_code,
                    "url": url,
                    "body": body,
                })
                
                err = str(body)
                if "invalid_grant" in err:
                    logger.error({
                        "event": "ML_INVALID_GRANT_ERROR",
                        "message": "Refresh token inválido ou expirado. Necessário reautenticação.",
                        "body": body
                    })
                    raise MeliAuthError(status_code, url, "invalid_grant")
                elif "invalid_request" in err:
                    logger.error({
                        "event": "ML_INVALID_REQUEST_ERROR",
                        "message": "Requisição inválida ao tentar renovar token",
                        "body": body
                    })
                    raise MeliAuthError(status_code, url, "invalid_request")
                else:
                    # Outros erros 4xx/5xx - tenta novamente com retry
                    raise MeliAuthError(status_code, url, f"HTTP {status_code}: {err}")
                    
            data = body
            new_access = data.get("access_token")
            new_refresh = data.get("refresh_token")
            expires_in = data.get("expires_in")
            token_type = data.get("token_type")
            scope = data.get("scope")
            user_id = data.get("user_id")
            
            # Mascara tokens para logging
            masked = dict(data)
            if "access_token" in masked and isinstance(masked["access_token"], str):
                masked["access_token"] = masked["access_token"][:6] + "***"
            if "refresh_token" in masked and isinstance(masked["refresh_token"], str):
                masked["refresh_token"] = masked["refresh_token"][:6] + "***"
                
            if new_access:
                logger.info({
                    "event": "IMPORT_MELI_TOKEN_REFRESH_OK",
                    "status": status_code,
                    "url": url,
                    "body": masked,
                })
                
                save_tokens_to_db(new_access, new_refresh, expires_in, token_type, scope, user_id)
                logger.info({"event": "ML_TOKENS_SAVED_DB"})
                
                return new_access, new_refresh
            else:
                logger.warning({"event": "IMPORT_MELI_TOKEN_REFRESH_FAIL", "status": status_code, "body": masked})
                return None, None

        except requests.exceptions.RequestException as e:
            logger.error({
                "event": "IMPORT_MELI_TOKEN_REFRESH_NETWORK_FAIL",
                "error": str(e),
                "response": getattr(e.response, "text", None),
                "url": url,
            })
            raise  # Re-raise para o retry mechanism capturar
            
    # Usa retry com backoff exponencial para renovação do token
    try:
        return retry_with_backoff(_refresh_token_internal, max_retries=3, base_delay=5, max_delay=60)
    except MeliAuthError as e:
        if "invalid_grant" in str(e):
            logger.error({
                "event": "ML_REFRESH_TOKEN_EXPIRED",
                "message": "Refresh token expirado. É necessário reautenticar com Mercado Livre.",
                "action_required": "Acesse /api/meli/auth para reautenticar"
            })
        raise

def exchange_tg_for_access_token(tg: str) -> str:
    settings = get_settings()
    url = f"{settings.ML_API_BASE_URL}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.ML_CLIENT_ID,
        "client_secret": settings.ML_CLIENT_SECRET,
        "code": tg,
        "redirect_uri": settings.ML_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        with _tg_exchange_lock:
            resp = requests.post(url, data=payload, headers=headers, timeout=15)
        status_code = resp.status_code
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        if status_code >= 400:
            body_excerpt = str(data)[:200]
            logger.error({
                "event": "ML_TG_EXCHANGE_FAIL",
                "status": status_code,
                "url": url,
                "body_excerpt": body_excerpt,
            })
            raise MeliAuthError(status_code, url, body_excerpt)

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        masked = dict(data)
        if isinstance(masked.get("access_token"), str):
            masked["access_token"] = masked["access_token"][:6] + "***"
        if isinstance(masked.get("refresh_token"), str):
            masked["refresh_token"] = masked["refresh_token"][:6] + "***"
        logger.info({
            "event": "ML_TG_EXCHANGE_OK",
            "status": status_code,
            "url": url,
            "body": masked,
        })

        expires_in = data.get("expires_in")
        token_type = data.get("token_type")
        scope = data.get("scope")
        user_id = data.get("user_id")
        now = datetime.utcnow()
        with Session(engine) as s:
            row = s.exec(select(MlToken).where(MlToken.id == 1)).first() or MlToken(id=1)
            row.access_token = access_token
            row.refresh_token = refresh_token
            row.expires_in = expires_in
            row.token_type = token_type
            row.scope = scope
            row.user_id = user_id
            row.updated_at = now
            if row.created_at is None:
                row.created_at = now
            s.add(row)
            s.commit()

        if not access_token:
            raise MeliAuthError(500, url, "Token de acesso ausente após troca TG")
        return access_token
    except requests.exceptions.RequestException as e:
        logger.error({
            "event": "ML_TG_EXCHANGE_ERR",
            "error": str(e),
            "response": getattr(e.response, "text", None),
            "url": url,
        })
        raise MeliAuthError(getattr(e.response, "status_code", 500) or 500, url, str(e))


def _auth_params(token: str) -> Dict[str, str]:
    return {"access_token": token}


def get_meli_products(limit: Optional[int] = None) -> List[Dict]:
    """
    Importa produtos do Mercado Livre com limite configurável e controle de taxa.
    Respeita 429 (Retry-After) e limita a 100 por execução (configurável).
    """
    settings = get_settings()
    token = get_access_token("read")  # Explicitamente usar leitura com Client Credentials
    seller_id = settings.ML_SELLER_ID
    headers = {"Authorization": f"Bearer {token}"}

    max_limit = int(limit or getattr(settings, "ML_IMPORT_LIMIT", 100))
    batch_size = 50  # limite típico por requisição
    all_items: List[str] = []
    offset = 0

    # Paginação de IDs
    while len(all_items) < max_limit:
        url = f"{settings.ML_API_BASE_URL}/users/{seller_id}/items/search"
        params = {"limit": batch_size, "offset": offset}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code == 429:
                retry = int(r.headers.get("Retry-After", 2))
                logger.info({"event": "ml_rate_limit", "stage": "list", "sleep": retry})
                time.sleep(retry)
                continue
            r.raise_for_status()
            data = r.json()
            ids = data.get("results", [])
            if not ids:
                break
            all_items.extend(ids)
            offset += batch_size
            # Segurança anti-bloqueio
            time.sleep(0.3)
            if len(all_items) >= max_limit:
                all_items = all_items[:max_limit]
                break
        except requests.RequestException as e:
            logger.error({"event": "ml_list_items_error", "error": str(e)})
            break

    # Busca detalhes de cada item com controle de taxa
    detailed: List[Dict] = []
    for item_id in all_items:
        item_url = f"{settings.ML_API_BASE_URL}/items/{item_id}"
        try:
            ir = requests.get(item_url, headers=headers, timeout=15)
            if ir.status_code == 429:
                retry = int(ir.headers.get("Retry-After", 3))
                logger.info({"event": "ml_rate_limit", "stage": "item", "sleep": retry, "item_id": item_id})
                time.sleep(retry)
                continue
            ir.raise_for_status()
            detailed.append(ir.json())
            time.sleep(0.25)
        except requests.RequestException as e:
            logger.error({"event": "ml_item_fetch_error", "item_id": item_id, "error": str(e)})
            continue
    return detailed


def normalize_meli_product(item: Dict) -> Dict:
    """Converte formato ML para padrão interno (Produto)."""
    return {
        "sku": str(item.get("id")),
        "titulo": item.get("title") or "Produto ML",
        "descricao": item.get("permalink"),
        "preco": float(item.get("price") or 0.0),
        "estoque_atual": int(item.get("available_quantity") or 0),
        "origem": "MERCADO_LIVRE",
        "status": "ATIVO",
    }


class RateLimiter:
    def __init__(self, rate_per_minute: int, concurrency: int):
        self.interval = max(60.0 / float(rate_per_minute), 0.01)
        self._last = 0.0
        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(concurrency)

    async def acquire(self):
        await self._sem.acquire()
        async with self._lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self._last
            sleep_for = self.interval - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            self._last = asyncio.get_running_loop().time()

    def release(self):
        self._sem.release()


def _truncate_body(data: Dict | str, max_len: int = 500) -> str:
    try:
        if isinstance(data, str):
            return data[:max_len]
        import json
        s = json.dumps(data, ensure_ascii=False)
        return s[:max_len]
    except Exception:
        return ""


def refresh_if_needed() -> None:
    with Session(engine) as s:
        row = s.exec(select(MlToken).where(MlToken.id == 1)).first()
    if row is None or (row and (row.expires_in is None or row.updated_at is None)):
        access, _ = refresh_access_token()
        return
    margin = 300
    if datetime.utcnow() >= row.updated_at + timedelta(seconds=int(row.expires_in or 0) - margin):
        access, _ = refresh_access_token()
        return


async def _fetch_json(session: aiohttp.ClientSession, url: str, headers: Dict[str, str], rl: RateLimiter, max_retries: int = 2) -> Optional[Dict]:
    for attempt in range(max_retries + 1):
        await rl.acquire()
        try:
            # Ensure friendly User-Agent for ML
            headers = dict(headers)
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", "2"))
                    logger.info({"event": "ml_rate_limit", "url": url, "sleep": retry_after})
                    rl.release()
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status == 401 and attempt == 0:
                    new_access, _ = refresh_access_token()
                    if new_access:
                        headers["Authorization"] = f"Bearer {new_access}"
                        logger.info({"event": "ML_API_REFRESH_OK", "url": url})
                        rl.release()
                        continue
                    logger.error({"event": "ML_API_REFRESH_FAIL", "url": url})
                data = await resp.json()
                rl.release()
                if resp.status in (401, 403):
                    body_excerpt = _truncate_body(data)
                    logger.error({"event": "IMPORT_MELI_FAIL", "status": resp.status, "endpoint": url, "body_excerpt": body_excerpt})
                    raise MeliAuthError(resp.status, url, body_excerpt)
                if resp.status >= 400:
                    logger.error({"event": "ml_fetch_error", "status": resp.status, "url": url, "body": data})
                    continue
                return data
        except asyncio.TimeoutError:
            rl.release()
            logger.error({"event": "ml_timeout", "url": url})
            continue
        except aiohttp.ClientError as e:
            rl.release()
            logger.error({"event": "ml_client_error", "url": url, "error": str(e)})
            continue
    return None


async def meli_request(method: str, endpoint: str, params: Optional[Dict] = None, session: Optional[aiohttp.ClientSession] = None, rl: Optional[RateLimiter] = None) -> Dict:
    settings = get_settings()
    base = getattr(settings, "ML_API_BASE_URL", "https://api.mercadolibre.com")
    token = get_access_token("read")  # Explicitamente usar leitura com Client Credentials
    headers = {"Authorization": f"Bearer {token}"}
    logger.info({"event": "ML_API_REQUEST", "method": method, "endpoint": endpoint, "params": params})
    if endpoint.startswith("http"):
        url = endpoint
    else:
        url = f"{base}{endpoint}"
    if params:
        from urllib.parse import urlencode
        qs = urlencode(params)
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}{qs}"
    owns_session = False
    if session is None:
        session = aiohttp.ClientSession()
        owns_session = True
    try:
        if rl is None:
            rl = RateLimiter(int(getattr(settings, "ML_RATE_LIMIT", 250)), 1)
        data = await _fetch_json(session, url, headers, rl)
        if data is None:
            raise RuntimeError("Falha ao obter dados do Mercado Livre")
        return data
    finally:
        if owns_session:
            await session.close()


async def importar_meli_async(limit: int = 100, dias: Optional[int] = None, novos: bool = False) -> Tuple[List[Dict], int]:
    settings = get_settings()
    logger.info({"event": "IMPORT_MELI_START", "limit": limit, "dias": dias, "novos": novos})
    seller_id = settings.ML_SELLER_ID

    max_limit = int(limit or getattr(settings, "ML_IMPORT_LIMIT", 100))
    batch_size = int(getattr(settings, "ML_IMPORT_BATCH", 100))
    collected_ids: List[str] = []
    offset = 0
    me_payload = await meli_request("GET", "/users/me")
    if not me_payload or not isinstance(me_payload, dict) or me_payload.get("id") is None:
        body_excerpt = _truncate_body(me_payload or {})
        logger.error({"event": "IMPORT_MELI_FAIL", "status": 0, "endpoint": f"{settings.ML_API_BASE_URL}/users/me", "body_excerpt": body_excerpt})
        raise MeliAuthError(0, f"{settings.ML_API_BASE_URL}/users/me", body_excerpt)
    page_num = 1
    while len(collected_ids) < max_limit:
        payload = await meli_request("GET", f"/users/{seller_id}/items/search", params={"status": "active", "limit": batch_size, "offset": offset})
        if not payload:
            break
        ids = payload.get("results", [])
        if not ids:
            break
        collected_ids.extend(ids)
        offset += batch_size
        logger.info({"event": "IMPORT_MELI_PAGE", "page": page_num, "count": len(ids)})
        page_num += 1
        if len(collected_ids) >= max_limit:
            collected_ids = collected_ids[:max_limit]
            break

    async def fetch_item(item_id: str) -> Optional[Dict]:
        return await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})

    tasks = [fetch_item(i) for i in collected_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict] = []
    for r in results:
        if isinstance(r, dict):
            status = r.get("status")
            if status != "active":
                continue
            if dias:
                last_updated = r.get("last_updated") or r.get("stop_time")
                try:
                    if last_updated:
                        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).replace(tzinfo=None)
                        if dt < datetime.utcnow() - timedelta(days=int(dias)):
                            continue
                except Exception:
                    pass
            items.append(r)
    return items, len(items)


def importar_meli(limit: int = 100, dias: Optional[int] = None, novos: bool = False) -> Dict:
    start = datetime.utcnow()
    # Determina modo
    mode = "FULL"
    if dias and int(dias) > 0:
        mode = "ULTIMOS_DIAS"
    elif novos:
        mode = "NOVOS"

    logger.info({"event": "IMPORT_MELI_MODE", "modo": mode, "limit": limit, "dias": dias, "novos": novos})

    items, fetched_count = asyncio.run(importar_meli_async(limit=limit, dias=dias, novos=novos))
    normalized: List[Dict] = []

    # Integração de snapshots e deduplicação
    novos_count = 0
    atualizados_count = 0
    ignorados_count = 0

    with next(get_session()) as session:
        for it in items:
            pictures = it.get("pictures") or []
            imagens = [p.get("secure_url") or p.get("url") for p in pictures if isinstance(p, dict)]
            base = normalize_meli_product(it)
            base["imagens"] = [u for u in imagens if u]

            sku = str(base.get("sku"))
            meli_id = str(it.get("id") or sku)
            status_meli = str(it.get("status") or "")
            item_hash = compute_meli_item_hash(base, it)

            snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
            if not snap:
                upsert_snapshot_new(session, sku, meli_id, item_hash, status_meli, {"id": it.get("id"), "title": it.get("title"), "price": it.get("price"), "status": it.get("status")})
                novos_count += 1
                logger.info({"event": "ML_ITEM_NEW", "sku": sku, "meli_id": meli_id})
                normalized.append(base)
                continue

            # Modo NOVOS: ignora qualquer item que já exista no snapshot (mesmo se mudou)
            if mode == "NOVOS":
                ignorados_count += 1
                logger.info({"event": "ML_ITEM_EXISTENTE_IGNORADO", "sku": sku, "meli_id": meli_id})
                continue

            if snap.hash_conteudo == item_hash:
                mark_snapshot_unchanged(session, snap)
                ignorados_count += 1
                logger.info({"event": "ML_ITEM_UNCHANGED", "sku": sku, "meli_id": meli_id})
                # Não adiciona para evitar reprocessamento
                continue

            update_snapshot_changed(session, snap, item_hash, status_meli, {"id": it.get("id"), "title": it.get("title"), "price": it.get("price"), "status": it.get("status")})
            atualizados_count += 1
            logger.info({"event": "ML_ITEM_CHANGED", "sku": sku, "meli_id": meli_id})
            normalized.append(base)

    tempo_exec = (datetime.utcnow() - start).total_seconds()
    try:
        # persiste log (mantém contrato existente)
        with next(get_session()) as session:
            log = MLLog(origem="MERCADO_LIVRE", total_importado=fetched_count, duracao_segundos=tempo_exec, status="sucesso")
            session.add(log)
            session.commit()
    except Exception as e:
        logger.error({"event": "ml_log_persist_error", "error": str(e)})

    logger.info({
        "event": "IMPORT_MELI_STATS",
        "fetched": fetched_count,
        "novos": novos_count,
        "atualizados": atualizados_count,
        "ignorados_sem_mudanca": ignorados_count,
        "modo": mode,
    })

    result = {
        "status": "sucesso",
        "importados": len(normalized),
        "origem": "Mercado Livre",
        "tempo_execucao": f"{round(tempo_exec,2)}s",
        "items": normalized,
    }
    logger.info({"event": "IMPORT_MELI_DONE", "importados": len(normalized), "duracao": result["tempo_execucao"]})
    return result


def importar_meli_todos_status(limit: Optional[int] = None, dias: Optional[int] = None) -> Dict:
    """
    Importa TODOS os produtos do Mercado Livre (ativos, vendidos, pausados, encerrados).
    Ideal para sincronização completa de grandes inventários (17k+ produtos).
    """
    start = datetime.utcnow()
    mode = "TODOS_STATUS"
    
    logger.info({"event": "IMPORT_MELI_TODOS_STATUS_MODE", "modo": mode, "limit": limit, "dias": dias})
    
    items, fetched_count = asyncio.run(importar_meli_todos_status_async(limit=limit, dias=dias))
    normalized: List[Dict] = []
    
    # Integração de snapshots e deduplicação
    novos_count = 0
    atualizados_count = 0
    ignorados_count = 0
    
    with next(get_session()) as session:
        for it in items:
            pictures = it.get("pictures") or []
            imagens = [p.get("secure_url") or p.get("url") for p in pictures if isinstance(p, dict)]
            base = normalize_meli_product(it)
            base["imagens"] = [u for u in imagens if u]
            
            # Adiciona informações de status do ML para sincronização em tempo real
            base["ml_status"] = it.get("status", "")
            base["ml_available_quantity"] = it.get("available_quantity", 0)
            base["ml_sold_quantity"] = it.get("sold_quantity", 0)
            base["ml_last_updated"] = it.get("last_updated", "")
            base["ml_stop_time"] = it.get("stop_time", "")
            
            sku = str(base.get("sku"))
            meli_id = str(it.get("id") or sku)
            status_meli = str(it.get("status") or "")
            item_hash = compute_meli_item_hash(base, it)
            
            snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
            if not snap:
                upsert_snapshot_new(session, sku, meli_id, item_hash, status_meli, {
                    "id": it.get("id"), 
                    "title": it.get("title"), 
                    "price": it.get("price"), 
                    "status": it.get("status"),
                    "available_quantity": it.get("available_quantity"),
                    "sold_quantity": it.get("sold_quantity"),
                    "last_updated": it.get("last_updated")
                })
                novos_count += 1
                logger.info({"event": "ML_ITEM_NEW_TODOS_STATUS", "sku": sku, "meli_id": meli_id, "status": status_meli})
                normalized.append(base)
                continue
            
            # Verifica se houve mudança no status ou quantidade (venda/reabastecimento)
            if (snap.hash_conteudo != item_hash or 
                snap.status_meli != status_meli or
                (it.get("sold_quantity") and it.get("sold_quantity") != getattr(snap, "sold_quantity", None))):
                
                update_snapshot_changed(session, snap, item_hash, status_meli, {
                    "id": it.get("id"), 
                    "title": it.get("title"), 
                    "price": it.get("price"), 
                    "status": it.get("status"),
                    "available_quantity": it.get("available_quantity"),
                    "sold_quantity": it.get("sold_quantity"),
                    "last_updated": it.get("last_updated")
                })
                atualizados_count += 1
                logger.info({"event": "ML_ITEM_CHANGED_TODOS_STATUS", "sku": sku, "meli_id": meli_id, "status": status_meli})
                normalized.append(base)
                continue
            
            mark_snapshot_unchanged(session, snap)
            ignorados_count += 1
            logger.info({"event": "ML_ITEM_UNCHANGED_TODOS_STATUS", "sku": sku, "meli_id": meli_id, "status": status_meli})
    
    tempo_exec = (datetime.utcnow() - start).total_seconds()
    try:
        with next(get_session()) as session:
            log = MLLog(origem="MERCADO_LIVRE_TODOS_STATUS", total_importado=fetched_count, duracao_segundos=tempo_exec, status="sucesso")
            session.add(log)
            session.commit()
    except Exception as e:
        logger.error({"event": "ml_log_persist_error_todos_status", "error": str(e)})
    
    logger.info({
        "event": "IMPORT_MELI_TODOS_STATUS_STATS",
        "fetched": fetched_count,
        "novos": novos_count,
        "atualizados": atualizados_count,
        "ignorados_sem_mudanca": ignorados_count,
        "modo": mode,
    })
    
    result = {
        "status": "sucesso",
        "importados": len(normalized),
        "origem": "Mercado Livre - Todos Status",
        "tempo_execucao": f"{round(tempo_exec, 2)}s",
        "items": normalized,
    }
    logger.info({"event": "IMPORT_MELI_TODOS_STATUS_DONE", "importados": len(normalized), "duracao": result["tempo_execucao"]})
    return result


def importar_meli_incremental(hours: int = 24) -> Dict:
    """
    Importa apenas produtos que foram modificados nas últimas horas.
    Ideal para sincronização incremental frequente (ex: a cada 15-30 minutos).
    """
    start = datetime.utcnow()
    mode = "INCREMENTAL"
    
    logger.info({"event": "IMPORT_MELI_INCREMENTAL_MODE", "modo": mode, "hours": hours})
    
    # Calcula data limite (ex: últimas 24 horas)
    since_date = start - timedelta(hours=hours)
    since_iso = since_date.isoformat() + "Z"
    
    items, fetched_count = asyncio.run(importar_meli_incremental_async(since_date=since_iso, hours=hours))
    normalized: List[Dict] = []
    
    # Integração de snapshots e deduplicação
    novos_count = 0
    atualizados_count = 0
    ignorados_count = 0
    
    with next(get_session()) as session:
        for it in items:
            pictures = it.get("pictures") or []
            imagens = [p.get("secure_url") or p.get("url") for p in pictures if isinstance(p, dict)]
            base = normalize_meli_product(it)
            base["imagens"] = [u for u in imagens if u]
            
            # Adiciona informações de status do ML para sincronização em tempo real
            base["ml_status"] = it.get("status", "")
            base["ml_available_quantity"] = it.get("available_quantity", 0)
            base["ml_sold_quantity"] = it.get("sold_quantity", 0)
            base["ml_last_updated"] = it.get("last_updated", "")
            base["ml_stop_time"] = it.get("stop_time", "")
            
            sku = str(base.get("sku"))
            meli_id = str(it.get("id") or sku)
            status_meli = str(it.get("status") or "")
            item_hash = compute_meli_item_hash(base, it)
            
            snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
            if not snap:
                upsert_snapshot_new(session, sku, meli_id, item_hash, status_meli, {
                    "id": it.get("id"), 
                    "title": it.get("title"), 
                    "price": it.get("price"), 
                    "status": it.get("status"),
                    "available_quantity": it.get("available_quantity"),
                    "sold_quantity": it.get("sold_quantity"),
                    "last_updated": it.get("last_updated")
                })
                novos_count += 1
                logger.info({"event": "ML_ITEM_NEW_INCREMENTAL", "sku": sku, "meli_id": meli_id, "status": status_meli})
                normalized.append(base)
                continue
            
            # Verifica se houve mudança no status ou quantidade (venda/reabastecimento)
            if (snap.hash_conteudo != item_hash or 
                snap.status_meli != status_meli or
                (it.get("sold_quantity") and it.get("sold_quantity") != getattr(snap, "sold_quantity", None))):
                
                update_snapshot_changed(session, snap, item_hash, status_meli, {
                    "id": it.get("id"), 
                    "title": it.get("title"), 
                    "price": it.get("price"), 
                    "status": it.get("status"),
                    "available_quantity": it.get("available_quantity"),
                    "sold_quantity": it.get("sold_quantity"),
                    "last_updated": it.get("last_updated")
                })
                atualizados_count += 1
                logger.info({"event": "ML_ITEM_CHANGED_INCREMENTAL", "sku": sku, "meli_id": meli_id, "status": status_meli})
                normalized.append(base)
                continue
            
            mark_snapshot_unchanged(session, snap)
            ignorados_count += 1
            logger.info({"event": "ML_ITEM_UNCHANGED_INCREMENTAL", "sku": sku, "meli_id": meli_id, "status": status_meli})
    
    tempo_exec = (datetime.utcnow() - start).total_seconds()
    try:
        with next(get_session()) as session:
            log = MLLog(origem="MERCADO_LIVRE_INCREMENTAL", total_importado=fetched_count, duracao_segundos=tempo_exec, status="sucesso")
            session.add(log)
            session.commit()
    except Exception as e:
        logger.error({"event": "ml_log_persist_error_incremental", "error": str(e)})
    
    logger.info({
        "event": "IMPORT_MELI_INCREMENTAL_STATS",
        "fetched": fetched_count,
        "novos": novos_count,
        "atualizados": atualizados_count,
        "ignorados_sem_mudanca": ignorados_count,
        "modo": mode,
        "hours": hours
    })
    
    result = {
        "status": "sucesso",
        "importados": len(normalized),
        "origem": "Mercado Livre - Incremental",
        "tempo_execucao": f"{round(tempo_exec, 2)}s",
        "items": normalized,
    }
    logger.info({"event": "IMPORT_MELI_INCREMENTAL_DONE", "importados": len(normalized), "duracao": result["tempo_execucao"]})
    return result


async def importar_meli_incremental_async(since_date: str, hours: int = 24) -> Tuple[List[Dict], int]:
    """
    Busca produtos do Mercado Livre que foram modificados após a data especificada.
    """
    settings = get_settings()
    seller_id = settings.ML_SELLER_ID
    batch_size = 50  # Limite do ML para items/search
    collected_ids = []
    offset = 0
    page_num = 1

    # Busca IDs com filtro de data (last_updated)
    while True:
        # Validar limite de offset do Mercado Livre (máximo 1000)
        if offset >= 1000:
            logger.warning({"event": "ML_OFFSET_LIMIT_REACHED", "offset": offset, "message": "Atingido limite máximo de offset (1000) da API do Mercado Livre. Considere usar search_type=scan para mais resultados."})
            break
            
        # Busca produtos atualizados recentemente (ativos e inativos)
        payload = await meli_request("GET", f"/users/{seller_id}/items/search", 
                                   params={
                                       "limit": batch_size, 
                                       "offset": offset,
                                       "since": since_date,  # Filtro por data de atualização
                                       "sort": "last_updated_desc"  # Ordena por mais recentes
                                   })
        
        if not payload:
            break
            
        ids = payload.get("results", [])
        if not ids:
            break
            
        collected_ids.extend(ids)
        offset += batch_size
        logger.info({"event": "IMPORT_MELI_INCREMENTAL_PAGE", "page": page_num, "count": len(ids), "total_coletado": len(collected_ids), "offset": offset})
        page_num += 1
        
        # Se pegou menos que batch_size, é a última página
        if len(ids) < batch_size:
            break

    # Busca detalhes de cada item com controle de taxa
    async def fetch_item(item_id: str) -> Optional[Dict]:
        return await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})

    tasks = [fetch_item(i) for i in collected_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict] = []
    
    for r in results:
        if isinstance(r, dict):
            items.append(r)
    
    return items, len(items)


async def importar_meli_todos_status_async(limit: Optional[int] = None, dias: Optional[int] = None) -> Tuple[List[Dict], int]:
    """
    Busca TODOS os produtos do Mercado Livre independente do status (ativo, vendido, pausado, etc).
    Ideal para sincronização completa de inventários grandes (17k+ produtos).
    
    🚨 CORRIGIDO: Agora usa múltiplas estratégias para contornar o limite de offset 1000
    """
    from app.services.meli_paginacao_fix import corrigir_paginacao_meli
    
    settings = get_settings()
    seller_id = settings.ML_SELLER_ID
    max_limit = limit or 50000  # Default 50k para cobrir 17k+ produtos
    
    print(f"🚀 Iniciando busca corrigida para {max_limit} produtos do seller {seller_id}")
    
    # 🎯 NOVA ESTRATÉGIA: Usar paginação corrigida que contorna o limite 1000
    collected_ids, total_encontrado = await corrigir_paginacao_meli(max_limit)
    
    print(f"📊 Total de IDs únicos encontrados: {len(collected_ids)}")
    
    # Se não encontrou muitos produtos, tentar estratégia alternativa
    if len(collected_ids) < 1000:
        print("⚠️ Poucos produtos encontrados, tentando estratégia de categorias...")
        # Buscar por categorias de auto peças principais
        categorias_auto = [
            "MLA5725",   # Acessórios para Veículos
            "MLA1744",   # Autos, Motos y Otros  
            "MLA11830",  # Repuestos y Accesorios
            "MLA119440", # Accesorios de Auto y Camioneta
            "MLA119441", # Accesorios para Motos
            "MLA119442", # Herramientas para Vehículos
            "MLA119443", # Lubricantes y Fluidos
            "MLA119444", # Performance
            "MLA119445", # Repuestos Carrocería
            "MLA119446", # Repuestos Motor
            "MLA119447", # Repuestos Suspensión y Dirección
            "MLA119448", # Repuestos Transmisión
            "MLA119449", # Rodados y Cubiertas
            "MLA119450", # Seguridad Vehicular
            "MLA119451", # Servicios para Vehículos
            "MLA119452", # Tuning y Modificación
        ]
        
        for categoria in categorias_auto[:8]:  # Limitar a 8 categorias principais
            if len(collected_ids) >= max_limit:
                break
                
            print(f"🔍 Buscando categoria {categoria}...")
            try:
                # Buscar produtos desta categoria deste vendedor
                params = {
                    "category": categoria,
                    "seller_id": seller_id,
                    "limit": 200,  # Limite por categoria
                    "offset": 0,
                    "sort": "relevance_desc"
                }
                
                payload = await meli_request("GET", f"/sites/MLB/search", params=params)
                if payload:
                    results = payload.get("results", [])
                    novos_ids = [item.get("id") for item in results if item.get("id") and item.get("id") not in collected_ids]
                    collected_ids.extend(novos_ids)
                    print(f"✅ Categoria {categoria}: {len(novos_ids)} produtos novos")
                    
                    # Pequena pausa entre categorias
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"⚠️ Erro na categoria {categoria}: {e}")
                continue
    
    # Buscar detalhes dos produtos encontrados
    print(f"📦 Buscando detalhes de {len(collected_ids)} produtos...")
    
    async def fetch_item(item_id: str) -> Optional[Dict]:
        try:
            return await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})
        except Exception as e:
            logger.error({"event": "ML_ITEM_FETCH_ERROR", "item_id": item_id, "error": str(e)})
            return None
    
    # Processar em lotes para não sobrecarregar a API
    items = []
    batch_size = 20  # Processar 20 por vez
    
    for i in range(0, len(collected_ids), batch_size):
        batch_ids = collected_ids[i:i+batch_size]
        tasks = [fetch_item(item_id) for item_id in batch_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result:
                items.append(result)
        
        # Progresso
        if (i + batch_size) % 100 == 0:
            print(f"📊 Processados {len(items)} produtos...")
        
        # Pequena pausa entre lotes
        if i + batch_size < len(collected_ids):
            await asyncio.sleep(0.1)
    
    print(f"✅ Finalizado: {len(items)} produtos detalhados obtidos")
    
    # Aplicar filtro de dias se necessário
    if dias:
        items_filtrados = []
        for item in items:
            last_updated = item.get("last_updated") or item.get("stop_time")
            try:
                if last_updated:
                    dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).replace(tzinfo=None)
                    if dt >= datetime.utcnow() - timedelta(days=int(dias)):
                        items_filtrados.append(item)
            except Exception:
                # Se não conseguir parsear a data, incluir o item
                items_filtrados.append(item)
        
        items = items_filtrados
        print(f"📅 Após filtro de {dias} dias: {len(items)} produtos")
    
    return items, len(items)


def importar_meli_from_ids(ids: List[str], dias: Optional[int] = None, mode: str = "FULL") -> Dict:
    items: List[Dict] = []
    async def _fetch(ids: List[str]) -> List[Dict]:
        async def fetch_item(item_id: str) -> Optional[Dict]:
            return await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})
        tasks = [fetch_item(i) for i in ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[Dict] = []
        for r in results:
            if isinstance(r, dict):
                status = r.get("status")
                if status != "active":
                    continue
                if dias:
                    last_updated = r.get("last_updated") or r.get("stop_time")
                    try:
                        if last_updated:
                            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).replace(tzinfo=None)
                            if dt < datetime.utcnow() - timedelta(days=int(dias)):
                                continue
                    except Exception:
                        pass
                out.append(r)
        return out
    items = asyncio.run(_fetch(ids))

    normalized: List[Dict] = []
    novos_count = 0
    atualizados_count = 0
    ignorados_count = 0

    with next(get_session()) as session:
        for it in items:
            pictures = it.get("pictures") or []
            imagens = [p.get("secure_url") or p.get("url") for p in pictures if isinstance(p, dict)]
            base = normalize_meli_product(it)
            base["imagens"] = [u for u in imagens if u]

            sku = str(base.get("sku"))
            meli_id = str(it.get("id") or sku)
            status_meli = str(it.get("status") or "")
            item_hash = compute_meli_item_hash(base, it)


            snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
            if not snap:
                upsert_snapshot_new(session, sku, meli_id, item_hash, status_meli, {"id": it.get("id"), "title": it.get("title"), "price": it.get("price"), "status": it.get("status")})
                novos_count += 1
                logger.info({"event": "ML_ITEM_NEW", "sku": sku, "meli_id": meli_id})
                normalized.append(base)
                continue

            if mode == "NOVOS":
                ignorados_count += 1
                logger.info({"event": "ML_ITEM_EXISTENTE_IGNORADO", "sku": sku, "meli_id": meli_id})
                continue

            if snap.hash_conteudo == item_hash:
                mark_snapshot_unchanged(session, snap)
                ignorados_count += 1
                logger.info({"event": "ML_ITEM_UNCHANGED", "sku": sku, "meli_id": meli_id})
                continue

            update_snapshot_changed(session, snap, item_hash, status_meli, {"id": it.get("id"), "title": it.get("title"), "price": it.get("price"), "status": it.get("status")})
            atualizados_count += 1
            logger.info({"event": "ML_ITEM_CHANGED", "sku": sku, "meli_id": meli_id})
            normalized.append(base)

    stats = {
        "fetched": len(items),
        "novos": novos_count,
        "atualizados": atualizados_count,
        "ignorados_sem_mudanca": ignorados_count,
        "modo": mode,
    }
    logger.info({"event": "IMPORT_MELI_STATS", "fetched": stats["fetched"], "novos": stats["novos"], "atualizados": stats["atualizados"], "ignorados_sem_mudanca": stats["ignorados_sem_mudanca"], "modo": stats["modo"]})
    return {"items": normalized, "stats": stats}

def import_user_items(limit: int = 1000, since_hours: int = 24) -> Dict:
    """
    Importa itens do usuário usando o novo sistema de tokens permanentes
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
        
        # Obter ID do vendedor
        settings = get_settings()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Buscar informações do usuário
        me_url = f"{settings.ML_API_BASE_URL}/users/me"
        me_response = requests.get(me_url, headers=headers, timeout=20)
        
        if me_response.status_code != 200:
            logger.error({
                "event": "IMPORT_MELI_AUTH_ERROR",
                "status": me_response.status_code,
                "url": me_url
            })
            raise Exception("Erro de autenticação ao buscar dados do usuário")
        
        user_data = me_response.json()
        seller_id = user_data.get("id")
        
        if not seller_id:
            raise Exception("Não foi possível obter ID do vendedor")
        
        logger.info({
            "event": "IMPORT_MELI_USER_FOUND",
            "seller_id": seller_id,
            "nickname": user_data.get("nickname")
        })
        
        # Calcular data de corte
        since_date = None
        if since_hours > 0:
            since_date = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
        
        # Buscar itens do vendedor
        all_items = []
        offset = 0
        batch_size = 50
        
        while offset < limit:
            current_batch_size = min(batch_size, limit - offset)
            
            logger.info({
                "event": "IMPORT_MELI_BATCH",
                "offset": offset,
                "limit": current_batch_size,
                "seller_id": seller_id
            })
            
            try:
                # Buscar IDs dos itens
                url = f"{settings.ML_API_BASE_URL}/users/{seller_id}/items/search"
                params = {
                    "limit": current_batch_size, 
                    "offset": offset,
                    "sort": "date_created_desc"
                }
                
                if since_date:
                    params["since"] = since_date
                
                response = requests.get(url, headers=headers, params=params, timeout=20)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    logger.info({
                        "event": "IMPORT_MELI_RATE_LIMIT",
                        "sleep": retry_after
                    })
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                items_ids = data.get("results", [])
                
                if not items_ids:
                    logger.info({
                        "event": "IMPORT_MELI_NO_MORE_ITEMS",
                        "offset": offset
                    })
                    break
                
                # Buscar detalhes de cada item
                for item_id in items_ids:
                    try:
                        # Buscar detalhes do item
                        item_url = f"{settings.ML_API_BASE_URL}/items/{item_id}"
                        item_response = requests.get(item_url, headers=headers, params={"include_attributes": "all"}, timeout=20)
                        
                        if item_response.status_code == 429:
                            retry_after = int(item_response.headers.get("Retry-After", 1))
                            time.sleep(retry_after)
                            continue
                        
                        if item_response.status_code != 200:
                            logger.warning({
                                "event": "IMPORT_MELI_ITEM_SKIPPED",
                                "item_id": item_id,
                                "status": item_response.status_code
                            })
                            continue
                        
                        item_details = item_response.json()
                        
                        # Aqui você processaria o item (salvar no banco, etc.)
                        all_items.append(item_details)
                        
                        logger.info({
                            "event": "IMPORT_MELI_ITEM_SUCCESS",
                            "item_id": item_id,
                            "title": item_details.get("title", "")[:50],
                            "price": item_details.get("price"),
                            "status": item_details.get("status")
                        })
                        
                        # Pequena pausa entre itens
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.error({
                            "event": "IMPORT_MELI_ITEM_ERROR",
                            "item_id": item_id,
                            "error": str(e)
                        })
                
                offset += current_batch_size
                
                # Pausa entre lotes
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


if __name__ == "__main__":
    print(refresh_access_token())
