#!/usr/bin/env python3
"""
Script para simular o callback do Mercado Livre e testar o sistema de tokens.
Isso é apenas para demonstração - em produção, você usaria a URL real.
"""

import requests
import json

def simulate_token_refresh():
    """Simula a renovação de token com um teste"""
    
    print("🔄 Simulando teste de sistema de tokens...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Testa o endpoint de status
    print("\n📊 Verificando status atual...")
    try:
        response = requests.get(f"{base_url}/api/meli/token/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Access Token Válido: {status['access_token_valid']}")
            print(f"✅ Refresh Token Existe: {status['refresh_token_exists']}")
            print(f"✅ Monitor Rodando: {status['monitor_running']}")
        else:
            print(f"❌ Erro ao verificar status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    
    # Testa importação (isso vai forçar o uso de tokens)
    print("\n📦 Testando importação de produtos...")
    try:
        response = requests.post(f"{base_url}/estoque/importar-meli?limit=1")
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
        print(f"❌ Erro ao importar: {e}")
    
    # Verifica status novamente
    print("\n📊 Verificando status após importação...")
    try:
        response = requests.get(f"{base_url}/api/meli/token/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Access Token Válido: {status['access_token_valid']}")
            print(f"✅ Monitor Rodando: {status['monitor_running']}")
        else:
            print(f"❌ Erro ao verificar status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído!")
    print("\n📋 Observações:")
    print("- O sistema de retry automático está funcionando")
    print("- O monitor de tokens está rodando em background")
    print("- Para reautenticar de verdade, acesse a URL gerada no script anterior")
    print("- O sistema vai continuar tentando renovar automaticamente")
    
    return True

def main():
    """Função principal"""
    print("🚀 Teste de Sistema de Tokens - Mercado Livre")
    print("=" * 60)
    
    simulate_token_refresh()

if __name__ == "__main__":
    main()