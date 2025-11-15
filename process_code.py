#!/usr/bin/env python3
"""
Script simples para trocar código TG - versão direta
"""

import requests
import json

def main():
    # Código fornecido
    code = "TG-691805c2b03fa5000148e9bc-434514569"
    
    print(f"🔄 Processando código: {code}")
    
    # Configurações
    client_id = "1201014348397159"
    client_secret = "LhQddeKMRVlrq1m7ShFj1HiAhN1KRf4V"
    redirect_uri = "https://dlautopecas.com.br/auth/meli/callback"
    
    # API do Mercado Livre
    token_url = "https://api.mercadolibre.com/oauth/token"
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri
    }
    
    print(f"📡 Enviando para: {token_url}")
    print(f"📋 Dados: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        
        print(f"\n✅ Status: {response.status_code}")
        print(f"📄 Resposta: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n🎉 SUCESSO!")
            print(f"Access Token: {result.get('access_token', '')[:20]}...")
            print(f"Refresh Token: {result.get('refresh_token', '')[:20]}...")
            print(f"Expires In: {result.get('expires_in', '')}")
            print(f"User ID: {result.get('user_id', '')}")
            
            # Atualizar backend
            update_tokens_backend(result)
            
        else:
            print(f"\n❌ Erro ao trocar código")
            
            # Verificar se é erro de código já usado
            if "invalid_grant" in response.text:
                print("💡 Código já foi usado ou expirou!")
                print("🔄 Você precisa gerar um novo código.")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def update_tokens_backend(tokens):
    """Atualiza tokens no backend via API"""
    
    print(f"\n🔄 Atualizando backend local...")
    
    try:
        # Endpoint para atualizar tokens (vamos criar um simples)
        backend_url = "http://localhost:8000/auth/meli/callback"
        
        # Simula o callback com os novos tokens
        params = {
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'expires_in': tokens.get('expires_in'),
            'user_id': tokens.get('user_id')
        }
        
        response = requests.get(backend_url, params=params, timeout=30)
        print(f"Backend update: {response.status_code}")
        
        # Testar novo token
        test_token(tokens.get('access_token'))
        
    except Exception as e:
        print(f"Erro ao atualizar backend: {e}")

def test_token(access_token):
    """Testa o token no /users/me"""
    
    if not access_token:
        return
        
    print(f"\n🧪 Testando token...")
    
    try:
        url = "https://api.mercadolibre.com/users/me"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            user = response.json()
            print(f"✅ Token VÁLIDO! Usuário: {user.get('nickname')} (ID: {user.get('id')})")
        else:
            print(f"❌ Token inválido: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Erro ao testar: {e}")

if __name__ == "__main__":
    main()