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
      await post(path);
    } catch (e: any) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h2>Sincronização Mercado Livre</h2>
      {error && <pre style={{ color: "red" }}>{error}</pre>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <button onClick={() => run("/estoque/importar-meli?novos=true")} disabled={!!loading} style={{ padding: 16 }}>
          {loading === "/estoque/importar-meli?novos=true" ? "Processando..." : "Anúncios Novos"}
        </button>
        <button onClick={() => run("/estoque/importar-meli?dias=15")} disabled={!!loading} style={{ padding: 16 }}>
          {loading === "/estoque/importar-meli?dias=15" ? "Processando..." : "Últimos 15 dias"}
        </button>
        <button onClick={() => run("/estoque/importar-meli?limit=500")} disabled={!!loading} style={{ padding: 16 }}>
          {loading === "/estoque/importar-meli?limit=500" ? "Processando..." : "Atualizar Tudo"}
        </button>
      </div>
      <div style={{ marginTop: 24 }}>
        <h4>Status</h4>
        <pre>{status ? JSON.stringify(status, null, 2) : "sem dados"}</pre>
      </div>
    </div>
  );
}

import withRoleGuard from "@/components/withRoleGuard";
export default withRoleGuard(SincronizacaoPage, { allowedRoles: ["anunciador", "gestor"] });
