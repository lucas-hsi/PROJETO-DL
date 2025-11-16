#!/usr/bin/env python3
"""
Script para monitorar o progresso total da importação de produtos do Mercado Livre
"""

import subprocess
import time
import json
from datetime import datetime

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
            # Extrair apenas o número da saída
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.isdigit():
                    return int(line)
        return 0
    except Exception as e:
        print(f"Erro ao consultar banco: {e}")
        return 0

def get_logs_importacao():
    """Pega logs recentes de importação"""
    try:
        result = subprocess.run([
            'docker-compose', 'logs', '--tail=10', 'backend'
        ], capture_output=True, text=True, cwd='C:\\PROJETO DL')
        
        if result.returncode == 0:
            return result.stdout
        return ""
    except Exception as e:
        return f"Erro ao pegar logs: {e}"

def main():
    print("🚀 Monitor de Importação DL Auto Peças")
    print("=" * 50)
    
    total_inicial = get_total_produtos()
    print(f"📊 Total inicial: {total_inicial} produtos")
    print(f"🎯 Meta: 17.000 produtos")
    print(f"📈 Progresso inicial: {(total_inicial/17000)*100:.1f}%")
    print()
    
    while True:
        total_atual = get_total_produtos()
        progresso = (total_atual/17000)*100
        
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] 📦 Total: {total_atual} produtos ({progresso:.1f}%) | ⬆️ +{total_atual-total_inicial}", end="")
        
        # Mostrar logs de importação a cada 5 minutos
        if datetime.now().minute % 5 == 0 and datetime.now().second < 30:
            print("\n📋 Logs recentes:")
            logs = get_logs_importacao()
            # Filtrar logs relevantes
            for line in logs.split('\n'):
                if any(keyword in line for keyword in ['IMPORT_', 'importado', 'fetched', 'novos']):
                    print(f"  {line.strip()}")
        
        time.sleep(30)  # Atualizar a cada 30 segundos

if __name__ == "__main__":
    main()