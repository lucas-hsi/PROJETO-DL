import React from "react";

type Health = {
  status: string;
  uptime?: number | null;
  version?: string | null;
};

export function HealthCard({ health }: { health: Health | null }) {
  if (!health) return <div className="card">Carregando...</div>;
  return (
    <div className="card" style={{ padding: 16, border: "1px solid #eee", borderRadius: 8 }}>
      <h3>API Status</h3>
      <p>Status: <b>{health.status}</b></p>
      <p>Uptime: {health.uptime ?? 0}s</p>
      <p>Versão: {health.version ?? "n/a"}</p>
    </div>
  );
}