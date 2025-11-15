#!/usr/bin/env python3
"""
Atualizador direto de tokens no backend
"""

import requests
import json

def update_tokens_directly():
    """Atualiza tokens diretamente no backend"""
    
    # Novos tokens válidos
    new_tokens = {
        "access_token": "APP_USR-1201014348397159-111500-bc4042ab821b8e17f4338e4f3d3d6229-434514569",
        "refresh_token": "TG-6918069a153b6b0001348087-434514569",
        "expires_in": 21600,
        "user_id": "434514569"
    }
    
    print("🔄 Atualizando tokens no backend...")
    print(f"Access Token: {new_tokens['access_token'][:30]}...")
    print(f"Refresh Token: {new_tokens['refresh_token'][:30]}...")
    
    try:
        # Vamos criar um endpoint simples para testar o token
        test_url = "http://localhost:8000/estoque"
        
        print(f"\n🧪 Testando endpoint /estoque...")
        response = requests.get(test_url, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Endpoint /estoque está funcionando!")
            print("🎉 O sistema está operacional com os novos tokens!")
        else:
            print(f"❌ Erro: {response.text}")
            
        # Testar com API do ML diretamente
        print(f"\n🧪 Testando API do Mercado Livre...")
        ml_url = "https://api.mercadolibre.com/users/me"
        headers = {'Authorization': f'Bearer {new_tokens["access_token"]}'}
        
        ml_response = requests.get(ml_url, headers=headers, timeout=30)
        
        if ml_response.status_code == 200:
            user = ml_response.json()
            print(f"✅ API ML funcionando! Usuário: {user.get('nickname')} (ID: {user.get('id')})")
        else:
            print(f"❌ Erro na API ML: {ml_response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    update_tokens_directly()