import React, { useEffect, useState } from "react";
import { getEstoque } from "../lib/api";

type Produto = {
  id: number;
  sku: string;
  titulo: string;
  preco: number;
  estoque_atual: number;
  origem: string;
};

export default function EstoquePage() {
  const [items, setItems] = useState<Produto[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEstoque(1, 20)
      .then((d) => setItems(d.items))
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h1>Estoque</h1>
      {error && <pre style={{ color: "red" }}>{error}</pre>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>SKU</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Título</th>
            <th style={{ textAlign: "right", borderBottom: "1px solid #eee" }}>Preço</th>
            <th style={{ textAlign: "right", borderBottom: "1px solid #eee" }}>Estoque</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Origem</th>
          </tr>
        </thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id}>
              <td style={{ padding: 8 }}>{p.sku}</td>
              <td style={{ padding: 8 }}>{p.titulo}</td>
              <td style={{ padding: 8, textAlign: "right" }}>{p.preco.toFixed(2)}</td>
              <td style={{ padding: 8, textAlign: "right" }}>{p.estoque_atual}</td>
              <td style={{ padding: 8 }}>{p.origem}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}