import React, { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function post(path: string) {
  const res = await fetch(`${API_URL}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}

async function get(path: string) {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

function SincronizacaoPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const iv = setInterval(() => {
      get("/estoque/meli/status").then(setStatus).catch(() => {});
    }, 3000);
    return () => clearInterval(iv);
  }, []);

  const run = async (path: string) => {
    setLoading(path);
    setError(null);
    try {
      const response = await post(path);
      
      // Adicionar feedback visual de sucesso
      if (response && typeof response === 'object') {
        if (response.importados !== undefined) {
          setStatus({
            ...status,
            ultima_importacao: {
              produtos: response.importados,
              tempo: response.tempo_execucao,
              timestamp: new Date().toISOString()
            }
          });
        } else if (response.message) {
          setStatus({
            ...status,
            ultima_operacao: {
              mensagem: response.message,
              timestamp: new Date().toISOString()
            }
          });
        }
      }
    } catch (e: any) {
      setError(`Erro: ${String(e)}`);
      console.error('Erro na sincronização:', e);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h1>🔄 Sincronização Mercado Livre</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Escolha o tipo de importação desejada. A importação completa busca todos os seus produtos (17k+), 
        enquanto as opções incrementais trazem apenas produtos atualizados recentemente.
      </p>
      {error && <pre style={{ color: "red", backgroundColor: '#fee', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>{error}</pre>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
        <button onClick={() => run("/estoque/importar-meli-todos-status")} disabled={!!loading} style={{ padding: 16, backgroundColor: '#4f46e5', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          {loading === "/estoque/importar-meli-todos-status" ? "Processando..." : "📦 Importar Todos (17k)"}
        </button>
        <button onClick={() => run("/estoque/importar-meli-incremental?hours=24")} disabled={!!loading} style={{ padding: 16, backgroundColor: '#0891b2', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          {loading === "/estoque/importar-meli-incremental?hours=24" ? "Processando..." : "🔄 Recentes (24h)"}
        </button>
        <button onClick={() => run("/estoque/importar-meli-incremental?hours=168")} disabled={!!loading} style={{ padding: 16, backgroundColor: '#0891b2', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          {loading === "/estoque/importar-meli-incremental?hours=168" ? "Processando..." : "📅 Últimos 7 dias"}
        </button>
        <button onClick={() => run("/meli/sync/todos-status-start")} disabled={!!loading} style={{ padding: 16, backgroundColor: '#dc2626', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          {loading === "/meli/sync/todos-status-start" ? "Processando..." : "⚡ Sync Completa (BG)"}
        </button>
        <button onClick={() => run("/meli/sync/incremental-start")} disabled={!!loading} style={{ padding: 16, backgroundColor: '#7c3aed', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          {loading === "/meli/sync/incremental-start" ? "Processando..." : "🔄 Sync Incremental"}
        </button>
      </div>
      <div style={{ marginTop: 32 }}>
        <h3>📊 Status da Sincronização</h3>
        {status ? (
          <div style={{ 
            backgroundColor: '#f8fafc', 
            padding: '16px', 
            borderRadius: '8px', 
            border: '1px solid #e2e8f0',
            fontSize: '14px'
          }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(status, null, 2)}
            </pre>
          </div>
        ) : (
          <p style={{ color: '#64748b', fontStyle: 'italic' }}>
            Nenhuma sincronização em andamento. Clique em um dos botões acima para iniciar.
          </p>
        )}
      </div>
    </div>
  );
}

import withRoleGuard from "@/components/withRoleGuard";
export default withRoleGuard(SincronizacaoPage, { allowedRoles: ["anunciador", "gestor"] });
