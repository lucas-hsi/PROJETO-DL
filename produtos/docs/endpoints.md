# Endpoints (inicial)

## Saúde
GET `/healthz`
Resposta:
```json
{ "status": "ok", "uptime": 1.234, "version": "0.1.0" }
```

## Estoque
GET `/estoque?page=1&size=10&sort_by=created_at&sort_dir=desc`
Resposta:
```json
{
  "items": [
    {
      "id": 1,
      "sku": "ABC-001",
      "titulo": "Filtro de Ar",
      "preco": 99.9,
      "estoque_atual": 10,
      "origem": "LOCAL",
      "status": "ATIVO",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

POST `/estoque`
Payload:
```json
{
  "sku": "ABC-001",
  "titulo": "Filtro de Ar",
  "preco": 99.9,
  "estoque_atual": 10,
  "origem": "LOCAL"
}
```