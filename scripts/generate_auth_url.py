#!/usr/bin/env python3
"""
Script para gerar URL de autorização do Mercado Livre quando o refresh token expira.
"""

import os
import sys
from urllib.parse import urlencode

def generate_auth_url():
    """Gera URL de autorização para Mercado Livre"""
    
    # Lê as configurações do arquivo .env
    env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
    
    client_id = None
    redirect_uri = None
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('ML_CLIENT_ID='):
                    client_id = line.split('=', 1)[1].strip().strip('"\'')
                elif line.startswith('ML_REDIRECT_URI='):
                    redirect_uri = line.split('=', 1)[1].strip().strip('"\'')
    except FileNotFoundError:
        print(f"❌ Arquivo .env não encontrado em: {env_path}")
        return None
    
    if not client_id or not redirect_uri:
        print("❌ ML_CLIENT_ID ou ML_REDIRECT_URI não encontrados no .env")
        return None
    
    # Gera URL de autorização
    auth_url = "https://auth.mercadolivre.com.br/authorization"
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri
    }
    
    full_url = f"{auth_url}?{urlencode(params)}"
    
    print("🔄 URL de Autorização Gerada:")
    print("=" * 60)
    print(full_url)
    print("=" * 60)
    print("\n📋 Instruções:")
    print("1. Abra a URL acima no navegador")
    print("2. Faça login com sua conta do Mercado Livre")
    print("3. Autorize o aplicativo")
    print("4. Você será redirecionado para uma URL com um código")
    print("5. Copie o código da URL (após 'code=')")
    print("6. Use o código no script de callback")
    
    return full_url

def main():
    """Função principal"""
    print("🚀 Gerador de URL de Autorização - Mercado Livre")
    print("=" * 60)
    
    url = generate_auth_url()
    
    if url:
        print(f"\n✅ URL gerada com sucesso!")
        print(f"\n🔗 URL: {url}")
    else:
        print("\n❌ Falha ao gerar URL")
        sys.exit(1)

if __name__ == "__main__":
    main()