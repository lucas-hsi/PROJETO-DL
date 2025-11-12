import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type Produto = {
  sku: string; titulo: string; preco: number; estoque: number;
  origem: string; data_importacao?: string;
};

export default function PainelAnunciadores() {
  const [status, setStatus] = useState<string>("Carregando...");
  const [itens, setItens] = useState<Produto[]>([]);
  const [busy, setBusy] = useState(false);

  const fetchSincronizado = async () => {
    try {
      const data = await apiGet<{ status: string; itens: Produto[] }>("/estoque/sincronizar");
      setStatus(data.status || "OK");
      setItens(data.itens || []);
    } catch (e: any) {
      setStatus(`Erro ao consultar estoque: ${e.message}`);
    }
  };

  const importarML = async () => {
    try {
      setBusy(true);
      await apiPost("/estoque/importar-meli");
      await fetchSincronizado();
      setStatus("Importação do Mercado Livre concluída.");
    } catch (e: any) {
      setStatus(`Falha ao importar ML: ${e.message}`);
    } finally { setBusy(false); }
  };

  const publicarShopify = async () => {
    try {
      setBusy(true);
      await apiPost("/estoque/publicar-shopify");
      await fetchSincronizado();
      setStatus("Publicação no Shopify concluída.");
    } catch (e: any) {
      setStatus(`Falha ao publicar Shopify: ${e.message}`);
    } finally { setBusy(false); }
  };

  useEffect(() => {
    fetchSincronizado();
    const t = setInterval(fetchSincronizado, 60000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Anunciadores — Operações</h1>

      <div className="flex gap-2">
        <button className="px-3 py-2 rounded bg-black text-white disabled:opacity-50"
          onClick={importarML} disabled={busy}>Importar do Mercado Livre</button>

        <button className="px-3 py-2 rounded bg-black text-white disabled:opacity-50"
          onClick={publicarShopify} disabled={busy}>Publicar no Shopify</button>

        <button className="px-3 py-2 rounded border" onClick={fetchSincronizado}>Atualizar</button>
      </div>

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

      {/* Espaço reservado para “Criar Anúncio” e “Otimização” em próximas fases */}
    </div>
  );
}