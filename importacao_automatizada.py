#!/usr/bin/env python3
"""
Script para automatizar múltiplas importações do Mercado Livre
"""

import subprocess
import time
import json
from datetime import datetime

def executar_importacao(endpoint, params=""):
    """Executa uma importação específica"""
    try:
        url = f"http://localhost:8000/estoque/{endpoint}{params}"
        result = subprocess.run([
            'powershell', '-Command', 
            f'Invoke-RestMethod -Uri "{url}" -Method Post'
        ], capture_output=True, text=True, cwd='C:\\PROJETO DL')
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout.strip())
                return {
                    "sucesso": True,
                    "importados": response.get("importados", 0),
                    "tempo": response.get("tempo_execucao", "0s"),
                    "endpoint": endpoint,
                    "params": params
                }
            except:
                return {
                    "sucesso": True,
                    "importados": 0,
                    "tempo": "0s",
                    "endpoint": endpoint,
                    "params": params,
                    "raw_response": result.stdout.strip()
                }
        else:
            return {
                "sucesso": False,
                "erro": result.stderr,
                "endpoint": endpoint,
                "params": params
            }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "endpoint": endpoint,
            "params": params
        }

def get_total_produtos():
    """Consulta o total de produtos no banco de dados"""
    try:
        result = subprocess.run([
            'docker-compose', 'exec', '-T', 'backend', 'python', '-c', '''
from app.models.produto import Produto
from sqlalchemy import func
from app.core.database import get_session

session = next(get_session())
total = session.query(func.count(Produto.id)).scalar()
session.close()
print(total)
'''
        ], capture_output=True, text=True, cwd='C:\\PROJETO DL')
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.isdigit():
                    return int(line)
        return 0
    except Exception as e:
        print(f"Erro ao consultar banco: {e}")
        return 0

def main():
    print("🚀 Iniciando Importações Automatizadas DL Auto Peças")
    print("=" * 60)
    
    total_inicial = get_total_produtos()
    print(f"📊 Total inicial: {total_inicial} produtos")
    print(f"🎯 Meta: 17.000 produtos")
    print(f"📈 Progresso inicial: {(total_inicial/17000)*100:.1f}%")
    print()
    
    # Lista de importações a executar
    importacoes = [
        ("importar-meli-todos-status", "?limit=25000"),  # Grande volume
        ("importar-meli-incremental", "?hours=96"),     # 4 dias
        ("importar-meli-todos-status", "?limit=20000&dias=14"),  # 2 semanas
        ("importar-meli-incremental", "?hours=168"),    # 7 dias
        ("importar-meli", "?limit=500&novos=true"),     # Apenas novos
        ("importar-meli-todos-status", "?limit=30000&dias=30"),  # 1 mês
    ]
    
    total_importados = 0
    
    for i, (endpoint, params) in enumerate(importacoes, 1):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Importação {i}/{len(importacoes)}: {endpoint}{params}")
        
        resultado = executar_importacao(endpoint, params)
        
        if resultado["sucesso"]:
            importados = resultado["importados"]
            total_importados += importados
            print(f"✅ Sucesso: {importados} produtos importados em {resultado['tempo']}")
            
            # Atualizar total
            total_atual = get_total_produtos()
            progresso = (total_atual/17000)*100
            print(f"📊 Total agora: {total_atual} produtos ({progresso:.1f}%)")
            
            # Aguardar entre importações para não sobrecarregar a API
            print(f"⏳ Aguardando 30 segundos...")
            time.sleep(30)
            
            # Se já atingimos 17.000, parar
            if total_atual >= 17000:
                print(f"🎉 Meta atingida! {total_atual} produtos importados!")
                break
        else:
            print(f"❌ Erro: {resultado['erro']}")
            print(f"⏳ Aguardando 60 segundos antes de continuar...")
            time.sleep(60)
    
    # Resumo final
    total_final = get_total_produtos()
    print(f"\n" + "="*60)
    print(f"🏁 RESUMO FINAL:")
    print(f"📊 Total inicial: {total_inicial} produtos")
    print(f"📈 Total final: {total_final} produtos")
    print(f"🎯 Progresso final: {(total_final/17000)*100:.1f}%")
    print(f"⬆️ Produtos novos: {total_final - total_inicial}")
    print(f"🚀 Faltam: {max(0, 17000 - total_final)} produtos para a meta")

if __name__ == "__main__":
    main()