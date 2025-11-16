#!/usr/bin/env python3
"""
Script para verificar o progresso da importação através dos logs
"""

import subprocess
import json
import re

def get_import_progress():
    """Verificar progresso da importação pelos logs"""
    try:
        # Pegar logs do docker
        result = subprocess.run(['docker-compose', 'logs', 'backend'], 
                                capture_output=True, text=True, cwd='c:\\PROJETO DL')
        
        if result.returncode != 0:
            print(f"❌ Erro ao pegar logs: {result.stderr}")
            return
        
        logs = result.stdout
        
        # Procurar por logs de importação
        import_logs = []
        for line in logs.split('\n'):
            if 'IMPORT_MELI_TODOS_STATUS' in line:
                import_logs.append(line)
        
        if not import_logs:
            print("📊 Nenhum log de importação encontrado")
            return
        
        # Analisar logs mais recentes
        total_importados = 0
        total_buscados = 0
        
        for log in import_logs[-20:]:  # Últimos 20 logs
            try:
                # Extrair JSON do log
                if 'event' in log and 'IMPORT_MELI_TODOS_STATUS_DONE' in log:
                    # Encontrar o JSON no log
                    match = re.search(r'\{.*\}', log)
                    if match:
                        data = json.loads(match.group())
                        if 'importados' in data:
                            total_importados = data['importados']
                
                if 'event' in log and 'IMPORT_MELI_TODOS_STATUS_STATS' in log:
                    match = re.search(r'\{.*\}', log)
                    if match:
                        data = json.loads(match.group())
                        if 'fetched' in data:
                            total_buscados = data['fetched']
                            
            except Exception as e:
                continue
        
        print(f"📊 RELATÓRIO DE IMPORTAÇÃO MERCADO LIVRE:")
        print(f"📦 Total de produtos buscados: {total_buscados}")
        print(f"✅ Total de produtos importados: {total_importados}")
        
        if total_buscados > 0:
            taxa_sucesso = (total_importados / total_buscados) * 100
            print(f"📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        # Ver logs mais recentes
        print(f"\n📝 Logs mais recentes:")
        for log in import_logs[-5:]:
            print(f"   {log.strip()}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    get_import_progress()