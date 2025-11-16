import psycopg2

try:
    # Conectar ao banco de dados
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="dl_autopecas",
        user="postgres",
        password="postgres123"
    )
    
    cursor = conn.cursor()
    
    # Contar produtos
    cursor.execute("SELECT COUNT(*) FROM produtos")
    count = cursor.fetchone()[0]
    
    print(f"📊 Total de produtos no banco: {count}")
    
    # Ver últimos produtos importados
    cursor.execute("SELECT sku, titulo, created_at FROM produtos ORDER BY created_at DESC LIMIT 5")
    produtos = cursor.fetchall()
    
    print("\n🔄 Últimos 5 produtos importados:")
    for produto in produtos:
        sku, titulo, created_at = produto
        print(f"  • {sku} - {titulo[:50]}... - {created_at}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro ao conectar ao banco: {e}")