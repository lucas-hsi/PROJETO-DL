"""
Script para trocar o authorization code por tokens (access/refresh) do Mercado Livre.
Execução:
    python meli_exchange_code.py

Passos:
1) Abra a URL de autorização impressa pelo script e faça login.
2) Após redirecionar, copie o parâmetro `code` da URL e cole no prompt.
3) O script troca o `code` por `access_token` e `refresh_token` e testa `/users/me`.
"""

import os
import sys
import json
from datetime import datetime, timedelta

import requests


ML_CLIENT_ID = os.getenv("ML_CLIENT_ID", "")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI", "https://dlautopecas.com.br/auth/meli/callback")
ML_API_BASE_URL = os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com")


def log(event: str, **kwargs):
    payload = {"event": event, "timestamp": datetime.utcnow().isoformat()}
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=False))


def auth_url() -> str:
    return (
        f"https://auth.mercadolibre.com.br/authorization?response_type=code"
        f"&client_id={ML_CLIENT_ID}&redirect_uri={ML_REDIRECT_URI}"
    )


def exchange_code(code: str):
    url = f"{ML_API_BASE_URL}/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    log("ML_CODE_EXCHANGE", status="tentativa", redirect_uri=ML_REDIRECT_URI)
    try:
        res = requests.post(url, data=data, headers=headers, timeout=15)
        res.raise_for_status()
        payload = res.json()
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        expires_in = int(payload.get("expires_in", 0))
        expira_em = datetime.now() + timedelta(seconds=expires_in)
        print("\n✅ TROCA DE CODE CONCLUÍDA!")
        print(f"Access Token : {access_token}")
        print(f"Refresh Token: {refresh_token}")
        print(f"Expira em    : {expira_em.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tempo (seg)  : {expires_in}\n")
        log("ML_CODE_EXCHANGE", status="sucesso", expires_in=expires_in, expira_em=expira_em.isoformat())
        teste_token(access_token)
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO ao trocar code por token: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print("Resposta:", e.response.text)
            except Exception:
                pass
        log("ML_CODE_EXCHANGE", status="falha", erro=str(e))


def teste_token(token: str):
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
    missing = []
    if not ML_CLIENT_ID:
        missing.append("ML_CLIENT_ID")
    if not ML_CLIENT_SECRET:
        missing.append("ML_CLIENT_SECRET")
    if missing:
        print("⚠️ ERRO: variáveis não definidas:", ", ".join(missing))
        print("Defina ML_CLIENT_ID e ML_CLIENT_SECRET antes de executar.")
        sys.exit(1)

    print("Abra a seguinte URL para autorizar o app e obter o code:")
    print(auth_url())
    code = input("Cole aqui o parâmetro 'code' retornado na URL: ").strip()
    if not code:
        print("⚠️ Code não informado.")
        sys.exit(1)
    exchange_code(code)