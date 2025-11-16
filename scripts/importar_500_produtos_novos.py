#!/usr/bin/env python3
"""
Script para forçar importação de 500 novos produtos do Mercado Livre
Autor: Sistema DL Auto Peças
Data: 2025-01-15

Este script busca produtos adicionais do Mercado Livre usando estratégias alternativas
e força a importação mesmo que já existam snapshots.
"""

import asyncio
import requests
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlmodel import Session, select

# Adicionar o diretório backend ao path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import engine, init_db
from app.core.config import get_settings
from app.core.logger import logger
from app.models.produto import Produto
from app.repositories.produto_repo import save_product
from app.repositories.meli_item_snapshot_repo import (
    get_snapshot_by_meli_id, 
    get_snapshot_by_sku,
    upsert_snapshot_new,
    update_snapshot_changed
)
from app.services.mercadolivre_service import meli_request, get_access_token
from app.services.meli_hash_utils import compute_meli_item_hash


class Importador500Produtos:
    def __init__(self):
        self.settings = get_settings()
        self.token = None
        self.seller_id = None
        self.produtos_importados = []
        self.stats = {
            'total_buscados': 0,
            'novos_importados': 0,
            'existentes_atualizados': 0,
            'erros': 0
        }
    
    async def inicializar(self):
        """Inicializa conexão e obtém token"""
        print("🚀 Inicializando importador de 500 produtos...")
        init_db()
        
        # Obter token de acesso
        self.token = get_access_token("read")
        if not self.token:
            raise Exception("❌ Não foi possível obter token válido")
        
        # Obter seller_id
        me_payload = await meli_request("GET", "/users/me")
        self.seller_id = me_payload.get("id")
        if not self.seller_id:
            raise Exception("❌ Não foi possível obter ID do vendedor")
        
        print(f"✅ Token obtido: {self.token[:10]}...")
        print(f"✅ Seller ID: {self.seller_id}")
    
    def normalize_meli_product(self, item: Dict) -> Dict:
        """Converte formato ML para padrão interno"""
        pictures = item.get("pictures") or []
        imagens = [p.get("secure_url") or p.get("url") for p in pictures if isinstance(p, dict)]
        
        return {
            "sku": str(item.get("id")),
            "titulo": item.get("title") or "Produto ML",
            "descricao": item.get("permalink", ""),
            "preco": float(item.get("price") or 0.0),
            "estoque_atual": int(item.get("available_quantity") or 0),
            "origem": "MERCADO_LIVRE",
            "status": "ATIVO",
            "imagens": [u for u in imagens if u][:5],  # Máximo 5 imagens
            "ml_status": item.get("status", ""),
            "ml_available_quantity": item.get("available_quantity", 0),
            "ml_sold_quantity": item.get("sold_quantity", 0),
            "ml_last_updated": item.get("last_updated", ""),
            "ml_category_id": item.get("category_id", ""),
            "ml_currency": item.get("currency_id", ""),
        }
    
    async def buscar_produtos_por_categoria(self, categoria: str, limite: int = 100) -> List[Dict]:
        """Busca produtos de uma categoria específica"""
        print(f"🔍 Buscando produtos da categoria: {categoria}")
        
        # Usar search API para buscar produtos por categoria
        params = {
            "category": categoria,
            "limit": 50,  # Máximo por página
            "offset": 0,
            "sort": "relevance",
            "status": "active"
        }
        
        produtos = []
        try:
            # Buscar IDs de produtos
            search_url = f"{self.settings.ML_API_BASE_URL}/sites/MLB/search"
            search_params = {
                "category": categoria,
                "limit": 50,
                "offset": 0,
                "sort": "relevance",
                "condition": "new",  # Apenas produtos novos
            }
            
            response = requests.get(search_url, params=search_params, headers={"Authorization": f"Bearer {self.token}"})
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                print(f"📊 Encontrados {len(results)} produtos na categoria {categoria}")
                
                # Buscar detalhes de cada produto
                for item in results[:limite]:
                    try:
                        item_id = item.get("id")
                        if item_id:
                            # Buscar detalhes completos
                            item_details = await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})
                            if item_details:
                                produtos.append(item_details)
                                print(f"✅ Produto adicionado: {item_details.get('title', '')[:50]}...")
                                
                                # Pequena pausa para não sobrecarregar a API
                                await asyncio.sleep(0.3)
                                
                                if len(produtos) >= limite:
                                    break
                    except Exception as e:
                        print(f"⚠️ Erro ao buscar detalhes do produto {item_id}: {e}")
                        continue
                        
        except Exception as e:
            print(f"⚠️ Erro ao buscar produtos da categoria {categoria}: {e}")
        
        return produtos
    
    async def buscar_produtos_populares(self, limite: int = 200) -> List[Dict]:
        """Busca produtos populares e em alta"""
        print("🔥 Buscando produtos populares...")
        
        produtos = []
        
        # Buscar produtos com diferentes critérios
        criterios = [
            {"sort": "sold_quantity", "order": "desc"},  # Mais vendidos
            {"sort": "price", "order": "asc"},          # Mais baratos
            {"sort": "price", "order": "desc"},         # Mais caros
            {"sort": "date_created", "order": "desc"},  # Mais recentes
        ]
        
        for criterio in criterios:
            if len(produtos) >= limite:
                break
                
            try:
                params = {
                    "seller_id": self.seller_id,
                    "limit": 50,
                    "offset": 0,
                    "status": "active",
                    **criterio
                }
                
                payload = await meli_request("GET", f"/users/{self.seller_id}/items/search", params=params)
                if payload:
                    ids = payload.get("results", [])
                    
                    # Buscar detalhes dos produtos
                    for item_id in ids[:20]:  # Máximo 20 por critério
                        try:
                            item_details = await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})
                            if item_details and item_details not in produtos:
                                produtos.append(item_details)
                                print(f"🔥 Produto popular: {item_details.get('title', '')[:50]}...")
                                
                                if len(produtos) >= limite:
                                    break
                                    
                        except Exception as e:
                            continue
                            
            except Exception as e:
                print(f"⚠️ Erro ao buscar produtos populares: {e}")
                continue
        
        return produtos[:limite]
    
    async def buscar_produtos_vendedores_similares(self, limite: int = 150) -> List[Dict]:
        """Busca produtos de vendedores similares"""
        print("🎯 Buscando produtos de vendedores similares...")
        
        produtos = []
        
        try:
            # Obter categorias dos produtos atuais
            with Session(engine) as session:
                produtos_atuais = session.exec(select(Produto).limit(10)).all()
                
                for produto in produtos_atuais:
                    if len(produtos) >= limite:
                        break
                        
                    # Buscar produtos similares por categoria ou palavras-chave
                    termos_busca = produto.titulo.split()[:3]  # Primeiras 3 palavras
                    termo = " ".join(termos_busca)
                    
                    search_url = f"{self.settings.ML_API_BASE_URL}/sites/MLB/search"
                    params = {
                        "q": termo,
                        "limit": 20,
                        "offset": 0,
                        "sort": "relevance",
                        "condition": "new"
                    }
                    
                    response = requests.get(search_url, params=params, headers={"Authorization": f"Bearer {self.token}"})
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        
                        for item in results[:10]:  # Máximo 10 por termo
                            try:
                                item_id = item.get("id")
                                if item_id:
                                    # Verificar se já não temos este produto
                                    existe = session.exec(select(Produto).where(Produto.sku == str(item_id))).first()
                                    if not existe:
                                        item_details = await meli_request("GET", f"/items/{item_id}", params={"include_attributes": "all"})
                                        if item_details:
                                            produtos.append(item_details)
                                            print(f"🎯 Produto similar encontrado: {item_details.get('title', '')[:50]}...")
                                            
                                            if len(produtos) >= limite:
                                                break
                                                
                            except Exception as e:
                                continue
                                
        except Exception as e:
            print(f"⚠️ Erro ao buscar produtos similares: {e}")
        
        return produtos[:limite]
    
    async def importar_produto_forcado(self, item: Dict) -> bool:
        """Força a importação de um produto, mesmo que exista"""
        try:
            # Normalizar produto
            produto_normalizado = self.normalize_meli_product(item)
            sku = produto_normalizado["sku"]
            meli_id = sku
            
            with Session(engine) as session:
                # Verificar se já existe
                produto_existente = session.exec(select(Produto).where(Produto.sku == sku)).first()
                
                if produto_existente:
                    # Atualizar produto existente
                    produto_existente.titulo = produto_normalizado["titulo"]
                    produto_existente.descricao = produto_normalizado["descricao"]
                    produto_existente.preco = produto_normalizado["preco"]
                    produto_existente.estoque_atual = produto_normalizado["estoque_atual"]
                    produto_existente.imagens = produto_normalizado["imagens"]
                    
                    session.add(produto_existente)
                    session.commit()
                    
                    self.stats["existentes_atualizados"] += 1
                    print(f"🔄 Produto atualizado: {sku} - {produto_normalizado['titulo'][:50]}...")
                else:
                    # Criar novo produto
                    save_product(session, produto_normalizado)
                    self.stats["novos_importados"] += 1
                    print(f"✅ Novo produto importado: {sku} - {produto_normalizado['titulo'][:50]}...")
                
                # Atualizar snapshot
                item_hash = compute_meli_item_hash(produto_normalizado, item)
                status_meli = item.get("status", "active")
                
                snap = get_snapshot_by_meli_id(session, meli_id) or get_snapshot_by_sku(session, sku)
                if snap:
                    update_snapshot_changed(session, snap, item_hash, status_meli, {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "price": item.get("price"),
                        "status": item.get("status"),
                        "available_quantity": item.get("available_quantity"),
                        "sold_quantity": item.get("sold_quantity"),
                        "last_updated": item.get("last_updated")
                    })
                else:
                    upsert_snapshot_new(session, sku, meli_id, item_hash, status_meli, {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "price": item.get("price"),
                        "status": item.get("status"),
                        "available_quantity": item.get("available_quantity"),
                        "sold_quantity": item.get("sold_quantity"),
                        "last_updated": item.get("last_updated")
                    })
                
                return True
                
        except Exception as e:
            self.stats["erros"] += 1
            print(f"❌ Erro ao importar produto {item.get('id', 'unknown')}: {e}")
            return False
    
    async def executar_importacao(self):
        """Executa a importação de 500 produtos"""
        print("\n🚀 INICIANDO IMPORTAÇÃO DE 500 PRODUTOS REAIS DO MERCADO LIVRE")
        print("=" * 70)
        
        await self.inicializar()
        
        # Estratégias para buscar produtos
        estrategias = [
            ("Produtos Populares", self.buscar_produtos_populares, 200),
            ("Produtos Similares", self.buscar_produtos_vendedores_similares, 150),
        ]
        
        # Categorias populares de auto peças
        categorias_auto_pecas = [
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
        
        todos_produtos = []
        
        # Executar estratégias
        for nome, funcao, limite in estrategias:
            print(f"\n📋 {nome}: Buscando {limite} produtos")
            try:
                produtos = await funcao(limite)
                todos_produtos.extend(produtos)
                print(f"✅ {nome}: {len(produtos)} produtos encontrados")
            except Exception as e:
                print(f"❌ Erro em {nome}: {e}")
        
        # Buscar por categorias de auto peças
        print(f"\n📋 Categorias Auto Peças: Buscando produtos por categoria")
        for categoria in categorias_auto_pecas[:5]:  # Limitar a 5 categorias
            if len(todos_produtos) >= 500:
                break
                
            try:
                produtos = await self.buscar_produtos_por_categoria(categoria, 50)
                todos_produtos.extend(produtos)
                print(f"✅ Categoria {categoria}: {len(produtos)} produtos")
                await asyncio.sleep(1)  # Pausa entre categorias
            except Exception as e:
                print(f"⚠️ Erro na categoria {categoria}: {e}")
                continue
        
        # Remover duplicados
        produtos_unicos = []
        skus_vistos = set()
        
        for produto in todos_produtos:
            sku = str(produto.get("id", ""))
            if sku and sku not in skus_vistos:
                skus_vistos.add(sku)
                produtos_unicos.append(produto)
        
        print(f"\n📊 Total de produtos únicos encontrados: {len(produtos_unicos)}")
        
        # Limitar a 500 produtos
        produtos_para_importar = produtos_unicos[:500]
        
        print(f"🎯 Importando {len(produtos_para_importar)} produtos...")
        
        # Importar produtos
        for i, produto in enumerate(produtos_para_importar, 1):
            print(f"\n[{i}/{len(produtos_para_importar)}] Importando produto...")
            await self.importar_produto_forcado(produto)
            
            # Pequena pausa entre importações
            if i % 10 == 0:
                print(f"⏰ Pequena pausa após {i} produtos...")
                await asyncio.sleep(0.5)
        
        # Relatório final
        print("\n" + "=" * 70)
        print("📊 RELATÓRIO FINAL DE IMPORTAÇÃO")
        print("=" * 70)
        print(f"✅ Total de produtos buscados: {self.stats['total_buscados']}")
        print(f"🆕 Novos produtos importados: {self.stats['novos_importados']}")
        print(f"🔄 Produtos existentes atualizados: {self.stats['existentes_atualizados']}")
        print(f"❌ Erros: {self.stats['erros']}")
        print(f"📦 Total processado: {sum(self.stats.values()) - self.stats['erros']}")
        
        # Verificar quantos produtos temos agora
        with Session(engine) as session:
            total_produtos = session.exec(select(func.count(Produto.id))).one()
            print(f"📈 Total geral de produtos no banco: {total_produtos}")
        
        print("\n🎉 Importação concluída com sucesso!")
        
        return {
            "sucesso": True,
            "novos_importados": self.stats["novos_importados"],
            "existentes_atualizados": self.stats["existentes_atualizados"],
            "total_geral": total_produtos
        }


async def main():
    """Função principal"""
    importador = Importador500Produtos()
    
    try:
        resultado = await importador.executar_importacao()
        return resultado
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        return {"sucesso": False, "erro": str(e)}


if __name__ == "__main__":
    # Executar script
    resultado = asyncio.run(main())
    
    if resultado["sucesso"]:
        print(f"\n✅ SCRIPT EXECUTADO COM SUCESSO!")
        print(f"🆕 Novos produtos: {resultado['novos_importados']}")
        print(f"🔄 Atualizados: {resultado['existentes_atualizados']}")
        print(f"📦 Total no banco: {resultado['total_geral']}")
    else:
        print(f"\n❌ FALHA NA EXECUÇÃO: {resultado.get('erro', 'Erro desconhecido')}")
        sys.exit(1)