# Integrações

## Mercado Livre
- Seed inicial via endpoint público `https://api.mercadolibre.com/sites/MLB/search?q=auto%20pecas`
- Mapeamento de campos: `id->sku`, `title->titulo`, `price->preco`, `available_quantity->estoque_atual`

## Shopify
- Planejada: autenticação via API Key/Secret, CRUD de produtos e webhooks.