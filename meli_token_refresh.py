"""
Script para renovar o access_token do Mercado Livre localmente.
Execução:
    python meli_token_refresh.py

Este script roda fora do Docker e usa variáveis de ambiente locais.
"""

import os
import json
import sys
from datetime import datetime, timedelta

import requests


# Configurações (substitua pelos valores reais do seu ambiente local)
ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN", "")
ML_API_BASE_URL = os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com")


def log(event: str, **kwargs):
    payload = {"event": event, "timestamp": datetime.utcnow().isoformat()}
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=False))


def refresh_token():
    print("🔁 Renovando token do Mercado Livre...")
    url = f"{ML_API_BASE_URL}/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": ML_REFRESH_TOKEN,
    }

    log("ML_TOKEN_REFRESH", status="tentativa", base_url=ML_API_BASE_URL)
    try:
        res = requests.post(url, data=data, timeout=15)
        res.raise_for_status()
        payload = res.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 0))
        refresh_token_new = payload.get("refresh_token")
        expira_em = datetime.now() + timedelta(seconds=expires_in)

        print("\n✅ TOKEN GERADO COM SUCESSO!")
        print(f"Access Token : {access_token}")
        print(f"Refresh Token: {refresh_token_new}")
        print(f"Expira em    : {expira_em.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tempo (seg)  : {expires_in}\n")

        log(
            "ML_TOKEN_REFRESH",
            status="sucesso",
            expires_in=expires_in,
            expira_em=expira_em.isoformat(),
        )

        # Testa o token com /users/me
        teste_token(access_token)

    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO ao renovar token: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print("Resposta:", e.response.text)
            except Exception:
                pass
        log("ML_TOKEN_REFRESH", status="falha", erro=str(e))


def teste_token(token: str):
    print("🧠 Testando token com /users/me...")
    url = f"{ML_API_BASE_URL}/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    log("ML_TOKEN_TEST", status="tentativa", endpoint="/users/me")
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        user = res.json()
        print("✅ Token válido!")
        print(f"Usuário: {user.get('nickname')} (ID {user.get('id')})")
        print(f"País: {user.get('country_id')}")
        log("ML_TOKEN_TEST", status="sucesso", user_id=user.get("id"), nickname=user.get("nickname"))
    except Exception as e:
        print(f"❌ Token inválido ou expirado: {e}")
        log("ML_TOKEN_TEST", status="falha", erro=str(e))


if __name__ == "__main__":
    # Validação básica das variáveis necessárias
    missing = []
    if not ML_CLIENT_ID:
        missing.append("ML_CLIENT_ID")
    if not ML_CLIENT_SECRET:
        missing.append("ML_CLIENT_SECRET")
    if not ML_REFRESH_TOKEN:
        missing.append("ML_REFRESH_TOKEN")

    if missing:
        print("⚠️ ERRO: variáveis não definidas:", ", ".join(missing))
        print("Defina as variáveis de ambiente antes de executar.")
        print("Exemplos:")
        print("Linux/macOS:")
        print("  export ML_CLIENT_ID=2100639007675605")
        print("  export ML_CLIENT_SECRET=BaQbQqjK0okWd9ldMlcvcjWxyk9l2PQ")
        print("  export ML_REFRESH_TOKEN=TG-XXXXXXXXXXXXXXXXXXXXXXXX")
        print("Windows (PowerShell):")
        print('  $env:ML_CLIENT_ID="2100639007675605"')
        print('  $env:ML_CLIENT_SECRET="BaQbQqjK0okWd9ldMlcvcjWxyk9l2PQ"')
        print('  $env:ML_REFRESH_TOKEN="TG-XXXXXXXXXXXXXXXXXXXXXXXX"')
        sys.exit(1)
    else:
        refresh_token()