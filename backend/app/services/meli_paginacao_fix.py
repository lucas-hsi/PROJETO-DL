"""
Módulo de correção da paginação do Mercado Livre
Resolve o problema do limite de offset 1000
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.core.logger import logger
from app.services.mercadolivre_service import meli_request
from app.core.config import get_settings


class MeliPaginacaoCorrigida:
    """
    Corrige a paginação do Mercado Livre para buscar todos os 17k+ produtos
    Usa múltiplas estratégias para contornar o limite de offset 1000
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.seller_id = self.settings.ML_SELLER_ID
        self.batch_size = 50  # Máximo permitido pela API
        
    async def buscar_todos_produtos(self, limit: Optional[int] = None) -> Tuple[List[str], int]:
        """
        Busca TODOS os produtos do vendedor usando múltiplas estratégias
        """
        max_limit = limit or 50000  # Default alto para cobrir 17k+ produtos
        collected_ids = set()  # Usar set para evitar duplicados
        
        print(f"🎯 Buscando todos os produtos do seller {self.seller_id}")
        
        # Estratégia 1: Busca por status (ativa + inativa)
        print("📋 Estratégia 1: Buscando por status...")
        for status in ["active", "paused", "closed", "sold", "under_review", "payment_required"]:
            ids = await self._buscar_por_status(status, max_limit)
            collected_ids.update(ids)
            print(f"✅ Status '{status}': {len(ids)} produtos encontrados")
            if len(collected_ids) >= max_limit:
                break
        
        # Estratégia 2: Busca por períodos de data (últimos 2 anos)
        print("📅 Estratégia 2: Buscando por períodos de data...")
        ids_data = await self._buscar_por_periodos(max_limit)
        collected_ids.update(ids_data)
        print(f"✅ Períodos de data: {len(ids_data)} produtos adicionais")
        
        # Estratégia 3: Busca por categorias principais
        print("🏷️ Estratégia 3: Buscando por categorias...")
        ids_categorias = await self._buscar_por_categorias(max_limit)
        collected_ids.update(ids_categorias)
        print(f"✅ Categorias: {len(ids_categorias)} produtos adicionais")
        
        # Estratégia 4: Busca com search_type=scan (se disponível)
        print("🔍 Estratégia 4: Buscando com search_type=scan...")
        ids_scan = await self._buscar_com_scan(max_limit)
        collected_ids.update(ids_scan)
        print(f"✅ Search scan: {len(ids_scan)} produtos adicionais")
        
        # Converter para lista e limitar
        all_ids = list(collected_ids)[:max_limit]
        
        print(f"🎯 Total de produtos únicos encontrados: {len(all_ids)}")
        return all_ids, len(all_ids)
    
    async def _buscar_por_status(self, status: str, max_limit: int) -> List[str]:
        """Busca produtos por status específico"""
        ids = []
        offset = 0
        
        while len(ids) < 2000:  # Limite por status para evitar excesso
            try:
                params = {
                    "status": status,
                    "limit": self.batch_size,
                    "offset": offset,
                    "sort": "date_created_desc"
                }
                
                payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
                if not payload:
                    break
                    
                results = payload.get("results", [])
                if not results:
                    break
                
                ids.extend(results)
                offset += self.batch_size
                
                # Parar se atingir offset 1000 ou limite
                if offset >= 1000 or len(ids) >= 2000:
                    break
                    
                # Pequena pausa para respeitar rate limit
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error({"event": "ML_STATUS_SEARCH_ERROR", "status": status, "error": str(e)})
                break
        
        return ids
    
    async def _buscar_por_periodos(self, max_limit: int) -> List[str]:
        """Busca produtos dividindo em períodos de tempo"""
        ids = []
        
        # Dividir últimos 2 anos em períodos de 30 dias
        dias_por_periodo = 30
        total_dias = 730  # 2 anos
        
        for dias_atras in range(0, total_dias, dias_por_periodo):
            if len(ids) >= max_limit:
                break
                
            try:
                data_fim = datetime.utcnow() - timedelta(days=dias_atras)
                data_inicio = data_fim - timedelta(days=dias_por_periodo)
                
                params = {
                    "limit": self.batch_size,
                    "offset": 0,
                    "since": data_inicio.isoformat(),
                    "until": data_fim.isoformat(),
                    "sort": "date_created_desc"
                }
                
                payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
                if payload:
                    results = payload.get("results", [])
                    novos_ids = [id for id in results if id not in ids]
                    ids.extend(novos_ids)
                    
                    logger.info({"event": "ML_PERIOD_SEARCH", "periodo": f"{data_inicio.date()} até {data_fim.date()}", "novos_ids": len(novos_ids), "total": len(ids)})
                
                # Pausa entre períodos
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error({"event": "ML_PERIOD_SEARCH_ERROR", "dias_atras": dias_atras, "error": str(e)})
                continue
        
        return ids
    
    async def _buscar_por_categorias(self, max_limit: int) -> List[str]:
        """Busca produtos pelas categorias principais do vendedor"""
        ids = []
        
        # Buscar categorias mais comuns do vendedor
        try:
            # Primeiro, pegar alguns produtos para identificar categorias
            params = {
                "limit": 50,
                "offset": 0,
                "status": "active",
                "sort": "relevance_desc"
            }
            
            payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
            if payload:
                results = payload.get("results", [])
                
                # Buscar detalhes dos produtos para identificar categorias
                for item_id in results[:10]:
                    try:
                        item_details = await meli_request("GET", f"/items/{item_id}")
                        if item_details:
                            category_id = item_details.get("category_id")
                            if category_id and len(ids) < max_limit:
                                # Buscar mais produtos desta categoria
                                category_ids = await self._buscar_por_categoria(category_id, max_limit - len(ids))
                                ids.extend([id for id in category_ids if id not in ids])
                    except Exception:
                        continue
        
        except Exception as e:
            logger.error({"event": "ML_CATEGORY_SEARCH_ERROR", "error": str(e)})
        
        return ids
    
    async def _buscar_por_categoria(self, category_id: str, limit: int) -> List[str]:
        """Busca produtos de uma categoria específica"""
        ids = []
        offset = 0
        
        while len(ids) < limit and offset < 1000:
            try:
                params = {
                    "category": category_id,
                    "seller_id": self.seller_id,
                    "limit": self.batch_size,
                    "offset": offset,
                    "sort": "relevance_desc"
                }
                
                payload = await meli_request("GET", f"/sites/MLB/search", params=params)
                if payload:
                    results = payload.get("results", [])
                    novos_ids = [item.get("id") for item in results if item.get("id") and item.get("id") not in ids]
                    ids.extend(novos_ids)
                    offset += self.batch_size
                else:
                    break
                    
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error({"event": "ML_CATEGORY_DETAIL_SEARCH_ERROR", "category": category_id, "error": str(e)})
                break
        
        return ids
    
    async def _buscar_com_scan(self, max_limit: int) -> List[str]:
        """Tenta usar search_type=scan se disponível"""
        ids = []
        
        try:
            # Tentar usar search_type=scan para buscar todos os resultados
            params = {
                "search_type": "scan",
                "limit": self.batch_size,
                "scroll_id": "initial",  # ID inicial para scan
                "sort": "none"  # Ordem não é garantida em scan
            }
            
            payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
            if payload:
                results = payload.get("results", [])
                scroll_id = payload.get("scroll_id")
                
                ids.extend(results)
                
                # Continuar buscando com scroll_id
                while scroll_id and len(ids) < max_limit:
                    params["scroll_id"] = scroll_id
                    params["limit"] = self.batch_size
                    
                    payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
                    if payload and payload.get("results"):
                        results = payload.get("results", [])
                        scroll_id = payload.get("scroll_id")
                        ids.extend([id for id in results if id not in ids])
                        
                        await asyncio.sleep(0.1)
                    else:
                        break
                        
                logger.info({"event": "ML_SCAN_SEARCH_SUCCESS", "total_ids": len(ids)})
        
        except Exception as e:
            logger.warning({"event": "ML_SCAN_SEARCH_NOT_AVAILABLE", "error": str(e), "message": "search_type=scan não disponível, usando outras estratégias"})
        
        return ids


async def corrigir_paginacao_meli(limit: Optional[int] = None) -> Tuple[List[str], int]:
    """
    Função principal para corrigir a paginação e buscar todos os produtos
    """
    paginador = MeliPaginacaoCorrigida()
    return await paginador.buscar_todos_produtos(limit)