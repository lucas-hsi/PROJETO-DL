import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading

import requests
import aiohttp
from app.core.config import get_settings
from app.core.logger import logger
from app.models.ml_log import MLLog
from app.core.database import get_session
from app.services.meli_hash_utils import compute_meli_item_hash
from app.repositories.meli_item_snapshot_repo import (
    get_snapshot_by_meli_id,
    get_snapshot_by_sku,
    upsert_snapshot_new,
    mark_snapshot_unchanged,
    update_snapshot_changed,
)

_tg_exchange_lock = threading.Lock()


def get_access_token() -> str:
    settings = get_settings()
    current = getattr(settings, "ML_ACCESS_TOKEN", "")
    refresh = getattr(settings, "ML_REFRESH_TOKEN", "")
    if current:
        try:
            r = requests.get(f"{getattr(settings, 'ML_API_BASE_URL', 'https://api.mercadolibre.com')}/users/me", headers={"Authorization": f"Bearer {current}"}, timeout=10)
            if r.status_code == 401:
                new_access, new_refresh = refresh_access_token()
                if not new_access:
                    raise MeliAuthError(401, f"{getattr(settings, 'ML_API_BASE_URL', 'https://api.mercadolibre.com')}/oauth/token", "invalid_grant ou token expirado")
                setattr(settings, "ML_ACCESS_TOKEN", new_access)
                if new_refresh:
                    setattr(settings, "ML_REFRESH_TOKEN", new_refresh)
                return new_access
            r.raise_for_status()
            logger.info({
                "event": "ML_ACCESS_TOKEN_USED",
                "status": "sucesso",
                "timestamp": datetime.utcnow().isoformat()
            })
            return current
        except requests.RequestException:
            new_access, new_refresh = refresh_access_token()
            if not new_access:
                raise MeliAuthError(401, f"{getattr(settings, 'ML_API_BASE_URL', 'https://api.mercadolibre.com')}/oauth/token", "invalid_grant ou token expirado")
            setattr(settings, "ML_ACCESS_TOKEN", new_access)
            if new_refresh:
                setattr(settings, "ML_REFRESH_TOKEN", new_refresh)
            return new_access

    new_access, _ = refresh_access_token()
    if not new_access:
        raise MeliAuthError(401, f"{getattr(settings, 'ML_API_BASE_URL', 'https://api.mercadolibre.com')}/oauth/token", "invalid_grant ou token expirado")
    return new_access


class MeliAuthError(Exception):
    def __init__(self, status: int, endpoint: str, body: str):
        self.status = status
        self.endpoint = endpoint
        self.body = body
        super().__init__(f"ML auth error {status} at {endpoint}")


def refresh_access_token() -> tuple[str | None, str | None]:
    settings = get_settings()
    url = f"{settings.ML_API_BASE_URL}/oauth/token"
    if isinstance(settings.ML_REFRESH_TOKEN, str) and settings.ML_REFRESH_TOKEN.startswith("TG-"):
        return None, None
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.ML_CLIENT_ID,
        "client_secret": settings.ML_CLIENT_SECRET,
        "refresh_token": settings.ML_REFRESH_TOKEN,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = requests.post(url, data=payload, headers=headers, timeout=15)
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
                raise MeliAuthError(status_code, url, "invalid_grant")
            return None, None
        data = body
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
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
            try:
                from app.api.routes.meli_auth import _persist_tokens_to_env
                if new_access:
                    setattr(settings, "ML_ACCESS_TOKEN", new_access)
                if new_refresh:
                    setattr(settings, "ML_REFRESH_TOKEN", new_refresh)
                _persist_tokens_to_env(new_access, new_refresh)
            except Exception as e:
                logger.error({"event": "ML_REFRESH_PERSIST_FAIL", "error": str(e)})
            return new_access, new_refresh
        logger.warning({"event": "IMPORT_MELI_TOKEN_REFRESH_FAIL", "status": status_code, "body": masked})
        return None, None

    except requests.exceptions.RequestException as e:
        logger.error({
            "event": "IMPORT_MELI_TOKEN_REFRESH_FAIL",
            "error": str(e),
            "response": getattr(e.response, "text", None),
            "url": url,
        })
        return None, None

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

        try:
            from app.api.routes.meli_auth import _persist_tokens_to_env
            if access_token:
                setattr(settings, "ML_ACCESS_TOKEN", access_token)
            if refresh_token:
                setattr(settings, "ML_REFRESH_TOKEN", refresh_token)
            _persist_tokens_to_env(access_token, refresh_token)
        except Exception as e:
            logger.error({"event": "ML_TG_PERSIST_FAIL", "error": str(e)})

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
    token = get_access_token()
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
    token = get_access_token()
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
        logger.info({"event": "IMPORT_MELI_INCREMENTAL_PAGE", "page": page_num, "count": len(ids), "total_coletado": len(collected_ids)})
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
    """
    settings = get_settings()
    seller_id = settings.ML_SELLER_ID
    batch_size = 50  # Limite do ML para items/search
    max_limit = limit or 20000  # Default 20k para cobrir 17k+ produtos
    collected_ids = []
    offset = 0
    page_num = 1

    # Busca IDs sem filtro de status para pegar TODOS os produtos
    while len(collected_ids) < max_limit:
        # Primeiro tenta ativos
        payload_active = await meli_request("GET", f"/users/{seller_id}/items/search", 
                                          params={"limit": batch_size, "offset": offset, "status": "active"})
        ids_active = payload_active.get("results", []) if payload_active else []
        
        # Depois busca inativos/encerrados em uma página separada
        payload_inactive = await meli_request("GET", f"/users/{seller_id}/items/search", 
                                            params={"limit": batch_size, "offset": offset, "status": "closed"})
        ids_inactive = payload_inactive.get("results", []) if payload_inactive else []
        
        # Combina e remove duplicados
        all_page_ids = list(set(ids_active + ids_inactive))
        
        if not all_page_ids:
            break
            
        collected_ids.extend(all_page_ids)
        offset += batch_size
        logger.info({"event": "IMPORT_MELI_TODOS_STATUS_PAGE", "page": page_num, "active": len(ids_active), "inactive": len(ids_inactive), "total_coletado": len(collected_ids)})
        page_num += 1
        
        if len(collected_ids) >= max_limit:
            collected_ids = collected_ids[:max_limit]
            break

    # Busca detalhes de cada item com controle de taxa
    async def fetch_item(item_id: str) -> Optional[Dict]:
        return await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})

    tasks = [fetch_item(i) for i in collected_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict] = []
    
    for r in results:
        if isinstance(r, dict):
            # Não filtra por status aqui - queremos TODOS os produtos
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

if __name__ == "__main__":
    print(refresh_access_token())
