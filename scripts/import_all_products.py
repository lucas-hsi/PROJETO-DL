#!/usr/bin/env python3
"""
Script para importar todos os produtos do Mercado Livre contornando o limite de offset (1000).
Usa estratégias alternativas como busca por data e categorias.
"""

import requests
import json
import time
from datetime import datetime, timedelta

def import_all_products_strategy():
    """Importa todos os produtos usando múltiplas estratégias"""
    
    print("🚀 Iniciando importação completa com estratégias alternativas...")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    total_imported = 0
    strategies_used = []
    
    # Estratégia 1: Importar por períodos (últimos 5 anos)
    print("\n📅 Estratégia 1: Importando por períodos...")
    
    periods = [
        ("últimos 30 dias", 30),
        ("últimos 90 dias", 90), 
        ("últimos 180 dias", 180),
        ("último 1 ano", 365),
        ("últimos 2 anos", 730),
        ("últimos 5 anos", 1825)
    ]
    
    for period_name, days in periods:
        print(f"\n  📊 Importando produtos dos {period_name}...")
        
        try:
            response = requests.post(f"{base_url}/estoque/importar-meli-incremental?limit=5000&dias={days}")
            
            if response.status_code == 200:
                result = response.json()
                imported = result.get('importados', 0)
                total_imported += imported
                strategies_used.append(f"{period_name}: {imported} produtos")
                print(f"    ✅ {imported} produtos importados")
            else:
                print(f"    ⚠️  Erro: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Erro: {e}")
    
    # Estratégia 2: Importar todos os status com limite menor (evita offset alto)
    print(f"\n📋 Estratégia 2: Importando todos os status...")
    
    try:
        # Primeiro tenta com limite menor para evitar offset alto
        response = requests.post(f"{base_url}/estoque/importar-meli-todos-status?limit=1000")
        
        if response.status_code == 200:
            result = response.json()
            imported = result.get('importados', 0)
            total_imported += imported
            strategies_used.append(f"Todos status (1k): {imported} produtos")
            print(f"    ✅ {imported} produtos importados")
        else:
            print(f"    ⚠️  Erro: {response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Erro: {e}")
    
    # Estratégia 3: Importação padrão com limite alto
    print(f"\n📦 Estratégia 3: Importação padrão...")
    
    try:
        response = requests.post(f"{base_url}/estoque/importar-meli?limit=5000")
        
        if response.status_code == 200:
            result = response.json()
            imported = result.get('importados', 0)
            total_imported += imported
            strategies_used.append(f"Importação padrão: {imported} produtos")
            print(f"    ✅ {imported} produtos importados")
        else:
            print(f"    ⚠️  Erro: {response.status_code}")
            
    except Exception as e:
        print(f"    ❌ Erro: {e}")
    
    # Relatório final
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO FINAL DE IMPORTAÇÃO")
    print("=" * 70)
    print(f"📦 Total de produtos importados: {total_imported}")
    print(f"🔢 Estratégias utilizadas: {len(strategies_used)}")
    
    if strategies_used:
        print("\n📋 Detalhes por estratégia:")
        for strategy in strategies_used:
            print(f"   • {strategy}")
    
    # Verificar quantos produtos temos no banco agora
    print(f"\n🔍 Verificando total no banco de dados...")
    try:
        response = requests.get(f"{base_url}/estoque/produtos/count")
        if response.status_code == 200:
            count_data = response.json()
            total_db = count_data.get('total', 0)
            print(f"📊 Total de produtos no banco: {total_db}")
        else:
            print("⚠️  Não foi possível verificar o total no banco")
    except Exception as e:
        print(f"❌ Erro ao verificar contagem: {e}")
    
    return total_imported

def main():
    """Função principal"""
    
    print("🎯 Importação Completa de Produtos - Mercado Livre")
    print("🔧 Usando múltiplas estratégias para contornar limites da API")
    
    total = import_all_products_strategy()
    
    print(f"\n🎉 Importação concluída! Total: {total} produtos")
    
    # Agora vamos testar uma sincronização incremental
    print(f"\n🔄 Testando sincronização incremental...")
    time.sleep(2)
    
    try:
        response = requests.post(f"http://localhost:8000/estoque/importar-meli-incremental?limit=100&hours=24")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sincronização incremental: {result.get('importados', 0)} produtos")
        else:
            print("⚠️  Sincronização incremental falhou")
    except Exception as e:
        print(f"❌ Erro na sincronização incremental: {e}")

if __name__ == "__main__":
    main()