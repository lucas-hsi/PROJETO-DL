#!/usr/bin/env python3
"""
Script para completar a autenticação com Mercado Livre usando o código TG.
"""

import requests
import sys

def complete_auth_with_tg(tg_code):
    """Completa a autenticação usando o código TG"""
    
    print(f"🔄 Completando autenticação com código: {tg_code[:20]}...")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Faz a requisição para o endpoint de callback
    try:
        # O endpoint espera o código como parâmetro 'code'
        response = requests.get(f"{base_url}/auth/meli/callback", params={"code": tg_code})
        
        print(f"📡 Status da requisição: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Autenticação completada com sucesso!")
            print("📄 Resposta:", response.text[:200])
            return True
        else:
            print(f"❌ Erro na autenticação: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 Detalhes do erro: {error_data}")
            except:
                print(f"📄 Resposta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao conectar ao servidor: {e}")
        return False

def verify_auth_status():
    """Verifica o status da autenticação"""
    
    print("\n🔍 Verificando status da autenticação...")
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/api/meli/token/status")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Access Token Válido: {status['access_token_valid']}")
            print(f"✅ Refresh Token Existe: {status['refresh_token_exists']}")
            print(f"✅ Monitor Rodando: {status['monitor_running']}")
            return status['access_token_valid']
        else:
            print(f"❌ Erro ao verificar status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return False

def main():
    """Função principal"""
    
    if len(sys.argv) > 1:
        tg_code = sys.argv[1]
    else:
        # Usa o código que você forneceu
        tg_code = "TG-69188b3c9247550001ac3d9f-434514569"
    
    print("🚀 Completando Autenticação - Mercado Livre")
    print("=" * 60)
    
    # Completa a autenticação
    success = complete_auth_with_tg(tg_code)
    
    # Verifica o status
    is_authenticated = verify_auth_status()
    
    print("\n" + "=" * 60)
    if success and is_authenticated:
        print("🎉 SUCESSO! Autenticação completada e tokens válidos!")
        print("\n✅ O sistema agora pode:")
        print("   • Importar produtos do Mercado Livre")
        print("   • Sincronizar estoque automaticamente")
        print("   • Rodar 24/7 sem erros de token")
    else:
        print("⚠️  A autenticação foi processada, mas os tokens ainda não estão válidos.")
        print("   Isso pode ser normal. O sistema vai continuar tentando automaticamente.")
    
    print("\n📋 Próximos passos:")
    print("   • Teste a importação de produtos")
    print("   • Monitore os logs para confirmar funcionamento")
    print("   • O sistema vai manter os tokens atualizados automaticamente")

if __name__ == "__main__":
    main()