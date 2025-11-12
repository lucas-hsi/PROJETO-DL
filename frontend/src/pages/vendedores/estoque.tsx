import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type Produto = {
  sku: string; titulo: string; preco: number; estoque: number;
  origem: string; data_importacao?: string;
};

export default function EstoqueVendedores() {
  const [status, setStatus] = useState<string>("Carregando...");
  const [itens, setItens] = useState<Produto[]>([]);

  const carregar = async () => {
    try {
      const data = await apiGet<{ status: string; itens: Produto[] }>("/estoque/sincronizar");
      setStatus(data.status || "OK");
      setItens(data.itens || []);
    } catch (e: any) {
      setStatus(`Erro ao carregar: ${e.message}`);
    }
  };

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 60000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Vendedores — Estoque</h1>
      <p className="text-sm text-gray-600">{status}</p>

      <div className="overflow-auto border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left p-2">SKU</th>
              <th className="text-left p-2">Título</th>
              <th className="text-left p-2">Preço</th>
              <th className="text-left p-2">Estoque</th>
              <th className="text-left p-2">Origem</th>
              <th className="text-left p-2">Atualização</th>
            </tr>
          </thead>
          <tbody>
            {itens.map((p, i) => (
              <tr key={i} className="border-b hover:bg-gray-50">
                <td className="p-2">{p.sku}</td>
                <td className="p-2">{p.titulo}</td>
                <td className="p-2">R$ {p.preco}</td>
                <td className="p-2">{p.estoque}</td>
                <td className="p-2">{p.origem}</td>
                <td className="p-2">{p.data_importacao || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}