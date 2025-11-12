import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")
ML_API_BASE_URL = os.getenv("ML_API_BASE_URL", "https://api.mercadolibre.com")
ENV_PATH = os.path.join(os.getcwd(), ".env")


def update_env_variable(key, new_value):
    """Atualiza o valor de uma variável no .env"""
    if not os.path.exists(ENV_PATH):
        print(f"⚠️ Arquivo .env não encontrado em {ENV_PATH}")
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={new_value}"
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count == 0:
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + replacement + "\n"
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ Variável {key} atualizada com sucesso no .env")


def refresh_tokens():
    """Renova tokens do Mercado Livre usando refresh_token atual"""
    print("🔁 Renovando token Mercado Livre...")
    url = f"{ML_API_BASE_URL}/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": ML_REFRESH_TOKEN,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = requests.post(url, data=payload, headers=headers)
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.status_code == 200 and "access_token" in data:
            print("\n✅ Tokens gerados com sucesso!")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            access = data["access_token"]
            refresh = data.get("refresh_token", ML_REFRESH_TOKEN)

            update_env_variable("ML_ACCESS_TOKEN", access)
            update_env_variable("ML_REFRESH_TOKEN", refresh)

            print("\n💾 Tokens salvos automaticamente no .env.")
            return True
        else:
            print("\n❌ Erro na requisição:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return False
    except Exception as e:
        print("🚨 Exceção inesperada:", e)
        return False


if __name__ == "__main__":
    ok = refresh_tokens()
    if ok:
        print("\n🎯 Renovação concluída com sucesso. Reinicie o backend.")
    else:
        print("\n⚠️ Falha na renovação. Verifique o código TG ou credenciais.")