#!/usr/bin/env python3
"""
Testar novo sistema de tokens permanentes do Mercado Livre
"""

import sys
import os
sys.path.append('/app')

from app.services.ml_token_manager import (
    ml_token_manager, 
    get_ml_token, 
    check_ml_token_status,
    notify_ml_token_renewal
)
from app.services.mercadolivre_service import get_access_token

def testar_novo_sistema_tokens():
    """Testar todas as funcionalidades do novo sistema"""
    print("🧪 Testando novo sistema de tokens permanentes...")
    print("=" * 60)
    
    # 1. Testar Client Credentials
    print("\n1️⃣ Testando Client Credentials...")
    try:
        cc_token = ml_token_manager.get_client_credentials_token()
        if cc_token:
            print(f"✅ Client Credentials OK: {cc_token[:20]}...")
        else:
            print("❌ Client Credentials falhou")
    except Exception as e:
        print(f"❌ Erro Client Credentials: {e}")
    
    # 2. Verificar status dos tokens
    print("\n2️⃣ Verificando status dos tokens...")
    try:
        status = check_ml_token_status()
        print("📊 Status dos tokens:")
        for key, value in status.items():
            print(f"   • {key}: {value}")
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
    
    # 3. Testar token para leitura
    print("\n3️⃣ Testando token para leitura...")
    try:
        read_token = get_access_token("read")
        if read_token:
            print(f"✅ Token leitura OK: {read_token[:20]}...")
        else:
            print("❌ Token leitura falhou")
    except Exception as e:
        print(f"❌ Erro token leitura: {e}")
    
    # 4. Testar notificação
    print("\n4️⃣ Testando notificação...")
    try:
        notify_ml_token_renewal()
        print("✅ Notificação testada")
    except Exception as e:
        print(f"❌ Erro notificação: {e}")
    
    # 5. Testar importação com novo sistema
    print("\n5️⃣ Testando importação com novo sistema...")
    try:
        # Importar apenas 5 produtos para teste
        from app.services.mercadolivre_service import import_user_items
        resultado = import_user_items(limit=5, since_hours=24)
        
        if resultado.get("success"):
            print(f"✅ Importação teste OK: {resultado.get('items_imported')} produtos")
        else:
            print(f"⚠️ Importação teste: {resultado.get('error')}")
    except Exception as e:
        print(f"❌ Erro importação teste: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Teste do novo sistema concluído!")
    print("\n📋 RESUMO:")
    print("• Client Credentials: Para leitura (sem refresh token)")
    print("• Authorization Code: Para escrita (com refresh token)")
    print("• Monitoramento: Alerta antes da expiração")
    print("• Fallback: Client Credentials se Authorization falhar")

if __name__ == "__main__":
    testar_novo_sistema_tokens()