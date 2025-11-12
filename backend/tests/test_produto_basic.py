from fastapi.testclient import TestClient
from app.main import app
import uuid


def test_crud_produto_basic():
    client = TestClient(app)
    sku = f"TEST-{uuid.uuid4().hex[:8]}"
    payload = {
        "sku": sku,
        "titulo": "Filtro de Ar",
        "preco": 99.90,
        "estoque_atual": 10,
        "origem": "LOCAL",
    }

    r = client.post("/estoque", json=payload)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["sku"] == sku

    rlist = client.get("/estoque")
    assert rlist.status_code == 200
    items = rlist.json()["items"]
    assert any(it["sku"] == sku for it in items)