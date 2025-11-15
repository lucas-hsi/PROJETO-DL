#!/usr/bin/env python3
"""
Script direto para trocar código TG com a API do Mercado Livre
Evita problemas de redirect_uri mismatch
"""

import requests
import json

def exchange_code_direct(code):
    """Troca código TG diretamente com a API do Mercado Livre"""
    
    # Configurações
    client_id = "1201014348397159"
    client_secret = "LhQddeKMRVlrq1m7ShFj1HiAhN1KRf4V"
    redirect_uri = "https://dlautopecas.com.br/auth/meli/callback"
    
    print(f"🔄 Trocando código: {code}")
    print(f"📡 Client ID: {client_id}")
    print(f"🔄 Redirect URI: {redirect_uri}")
    
    # API do Mercado Livre
    token_url = "https://api.mercadolibre.com/oauth/token"
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri
    }
    
    try:
        print(f"\n📡 Enviando requisição para: {token_url}")
        print(f"📋 Dados: {json.dumps(data, indent=2)}")
        
        response = requests.post(token_url, data=data, timeout=30)
        
        print(f"\n✅ Resposta da API:")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n🎉 SUCESSO! Tokens recebidos:")
            print(json.dumps(result, indent=2))
            
            # Atualizar no backend local
            update_backend_tokens(result)
            
        else:
            print(f"\n❌ Erro: {response.status_code}")
            print(f"Resposta: {response.text}")
            
            # Tentar parse do erro
            try:
                error_data = response.json()
                print(f"Erro detalhado: {json.dumps(error_data, indent=2)}")
            except:
                pass
            
    except Exception as e:
        print(f"\n❌ Erro ao conectar com API: {e}")

def update_backend_tokens(tokens):
    """Atualiza tokens no backend local"""
    
    print(f"\n🔄 Atualizando tokens no backend local...")
    
    try:
        # Prepara dados para atualização
        update_data = {
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'expires_in': tokens.get('expires_in'),
            'user_id': tokens.get('user_id')
        }
        
        print(f"Tokens para atualizar: {json.dumps(update_data, indent=2)}")
        
        # Vamos criar um endpoint simples no backend para atualizar
        # Por enquanto, vamos apenas mostrar como atualizar manualmente
        print(f"\n📋 Para atualizar manualmente no .env:")
        print(f"ML_ACCESS_TOKEN={tokens.get('access_token')}")
        print(f"ML_REFRESH_TOKEN={tokens.get('refresh_token')}")
        
        # Testar o novo token
        test_new_token(tokens.get('access_token'))
        
    except Exception as e:
        print(f"❌ Erro ao atualizar: {e}")

def test_new_token(access_token):
    """Testa o novo token"""
    
    print(f"\n🧪 Testando novo token...")
    
    try:
        # Testa com /users/me
        test_url = "https://api.mercadolibre.com/users/me"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(test_url, headers=headers, timeout=30)
        
        print(f"Teste /users/me: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Token válido! Usuário: {user_data.get('nickname')} (ID: {user_data.get('id')})")
        else:
            print(f"❌ Token inválido: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro ao testar token: {e}")

def main():
    print("🎯 Trocador Direto de Código Mercado Livre")
    print("=" * 50)
    
    code = input("\n📋 Cole o código de autorização (TG-...): ").strip()
    
    if not code:
        print("❌ Código não fornecido!")
        return
    
    if not code.startswith("TG-"):
        print("⚠️  Atenção: O código deve começar com 'TG-'")
    
    exchange_code_direct(code)

if __name__ == "__main__":
    main()