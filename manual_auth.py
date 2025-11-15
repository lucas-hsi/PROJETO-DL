#!/usr/bin/env python3
"""
Script manual para processar código de autorização do Mercado Livre
Use quando o callback externo não estiver disponível
"""

import requests
import sys
import os

def process_auth_code(code):
    """Processa código de autorização e troca por tokens"""
    
    # Configurações do .env
    client_id = "1201014348397159"
    client_secret = "LhQddeKMRVlrq1m7ShFj1HiAhN1KRf4V"
    redirect_uri = "https://dlautopecas.com.br/auth/meli/callback"
    
    print(f"🔄 Processando código: {code}")
    print(f"📡 Client ID: {client_id}")
    print(f"🔄 Redirect URI: {redirect_uri}")
    
    # URL do backend local
    backend_url = "http://localhost:8000/auth/meli/callback"
    
    try:
        # Simula o callback com o código
        response = requests.get(backend_url, params={"code": code}, timeout=30)
        
        print(f"\n✅ Resposta do servidor:")
        print(f"Status: {response.status_code}")
        print(f"Conteúdo: {response.text}")
        
        if response.status_code == 200:
            print("\n🎉 SUCESSO! Tokens trocados com sucesso!")
            print("\n📊 Verificando tokens...")
            
            # Verifica os tokens atuais
            debug_response = requests.get("http://localhost:8000/meli/debug-token")
            if debug_response.status_code == 200:
                print(f"Tokens atuais: {debug_response.text}")
            
        else:
            print(f"\n❌ Erro: {response.status_code}")
            print(f"Detalhes: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Erro ao conectar com backend: {e}")
        print("\n💡 Verifique se o backend está rodando em http://localhost:8000")

def main():
    print("🎯 Processador Manual de Autorização Mercado Livre")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = input("\n📋 Cole o código de autorização (TG-...): ").strip()
    
    if not code:
        print("❌ Código não fornecido!")
        return
    
    if not code.startswith("TG-"):
        print("⚠️  Atenção: O código deve começar com 'TG-'")
    
    process_auth_code(code)

if __name__ == "__main__":
    main()