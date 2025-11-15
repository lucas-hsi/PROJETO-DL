import { useEffect, useState } from "react";
import styled from "styled-components";
import { Button } from "@/components/ui/Button";
import { Table } from "@/components/ui/Table";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { apiGet, apiPost, API_URL } from "@/lib/api";

type Produto = {
  sku: string; titulo: string; preco: number; estoque: number;
  origem: string; data_importacao?: string;
};

const Wrap = styled.div`
  padding: 24px;
`;

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
      const res = await fetch(`${API_URL}/estoque/importar-meli?limit=100`, { method: "POST" });
      if (!res.ok) {
        let msg = `Falha na importação.`;
        try {
          const err = await res.json();
          if (err && err.detail && err.detail.tipo === "ML_AUTH") {
            msg = `Falha na importação (ML_AUTH ${err.detail.http_status}): verifique credenciais/escopos. Endpoint: ${err.detail.endpoint}`;
          }
        } catch {}
        setStatus(msg);
        return;
      }
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

  const columns = [
    { key: 'sku' as keyof Produto, header: 'SKU' },
    { key: 'titulo' as keyof Produto, header: 'Título' },
    { key: 'preco' as keyof Produto, header: 'Preço', render: (v: number) => `R$ ${v}` },
    { key: 'estoque' as keyof Produto, header: 'Estoque' },
    { key: 'origem' as keyof Produto, header: 'Origem' },
    { key: 'data_importacao' as keyof Produto, header: 'Atualização', render: (v?: string) => v || '-' },
  ];

  return (
    <Wrap>
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Anunciadores — Operações</CardTitle>
            <CardDescription>Ações de sincronização e publicação</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <Button onClick={importarML} disabled={busy}>Importar do Mercado Livre</Button>
            <Button onClick={publicarShopify} disabled={busy}>Publicar no Shopify</Button>
            <Button variant="secondary" onClick={fetchSincronizado}>Atualizar</Button>
            <a href="/diagnostics" style={{ alignSelf: 'center', fontSize: 13 }}>Ver Diagnóstico</a>
          </div>
          <div style={{ fontSize: 13, marginBottom: 12 }}>{status}</div>
          <Table data={itens} columns={columns} itemsPerPage={20} />
        </CardContent>
      </Card>
    </Wrap>
  );
}