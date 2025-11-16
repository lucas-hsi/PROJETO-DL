#!/usr/bin/env python3
"""
Script de diagnóstico para testar o sistema de tokens do Mercado Livre.
Verifica se os tokens estão funcionando corretamente e testa a renovação.
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_token_endpoints():
    """Testa os endpoints de token do backend"""
    base_url = "http://localhost:8000"
    
    print("🔍 Iniciando diagnóstico de tokens do Mercado Livre...")
    print("=" * 60)
    
    # Testa status do token
    print("\n📊 Verificando status dos tokens...")
    try:
        response = requests.get(f"{base_url}/api/meli/token/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Access Token Válido: {status['access_token_valid']}")
            print(f"✅ Refresh Token Existe: {status['refresh_token_exists']}")
            print(f"✅ Monitor Rodando: {status['monitor_running']}")
            print(f"ℹ️  Mensagem: {status['message']}")
        else:
            print(f"❌ Erro ao verificar status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro ao conectar ao backend: {e}")
        return False
    
    # Testa renovação manual
    print("\n🔄 Testando renovação manual de token...")
    try:
        response = requests.post(f"{base_url}/api/meli/token/refresh")
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Token renovado com sucesso!")
                print(f"ℹ️  Preview Access Token: {result['access_token_preview']}")
                if result['refresh_token_preview']:
                    print(f"ℹ️  Preview Refresh Token: {result['refresh_token_preview']}")
            else:
                print(f"⚠️  Renovacao falhou: {result['message']}")
        else:
            print(f"❌ Erro ao renovar token: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Erro ao renovar token: {e}")
    
    # Testa importação de produtos
    print("\n📦 Testando importação de produtos...")
    try:
        response = requests.post(f"{base_url}/api/meli/importar?limit=5")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Importação realizada com sucesso!")
            print(f"ℹ️  Produtos importados: {result['importados']}")
            print(f"ℹ️  Tempo de execução: {result['tempo_execucao']}")
        else:
            print(f"⚠️  Importação falhou: {response.status_code}")
            error_data = response.json()
            if 'detail' in error_data:
                print(f"ℹ️  Erro: {error_data['detail']}")
    except Exception as e:
        print(f"❌ Erro ao importar produtos: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Diagnóstico concluído!")
    return True

def test_continuous_operation():
    """Testa operação contínua por alguns minutos"""
    print("\n⏱️  Testando operação contínua por 5 minutos...")
    print("(Isso vai verificar se os tokens continuam válidos)")
    
    base_url = "http://localhost:8000"
    start_time = time.time()
    test_duration = 300  # 5 minutos
    
    while time.time() - start_time < test_duration:
        try:
            # Testa status do token
            response = requests.get(f"{base_url}/api/meli/token/status")
            if response.status_code == 200:
                status = response.json()
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] ✅ Tokens OK - Access: {status['access_token_valid']}, Monitor: {status['monitor_running']}")
            else:
                print(f"❌ Erro ao verificar status: {response.status_code}")
            
            # Aguarda 30 segundos
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n⏹️  Teste interrompido pelo usuário")
            break
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] ❌ Erro: {e}")
            time.sleep(30)
    
    print("✅ Teste de operação contínua concluído!")

def main():
    """Função principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        test_continuous_operation()
    else:
        test_token_endpoints()

if __name__ == "__main__":
    main()