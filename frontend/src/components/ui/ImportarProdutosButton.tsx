"use client";
import React, { useState } from "react";
import styled from "styled-components";
import { colors, shadows } from "@/styles/tokens";
import { Button } from "@/components/ui/Button";
import { apiPost } from "@/lib/api";

interface Props {
  onFinish?: () => void;
}

const StatusBox = styled.div`
  margin-top: 16px;
  font-size: 0.9rem;
  color: ${colors.textDark};
  background: rgba(255,255,255,0.85);
  padding: 12px 16px;
  border-radius: 10px;
  box-shadow: ${shadows.base};
`;

export default function ImportarProdutosButton({ onFinish }: Props) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleImport = async () => {
    setLoading(true);
    setStatus("⏳ Iniciando importação de produtos...");
    try {
      const data = await apiPost<{ importados: number; tempo_execucao: string }>(
        "/estoque/importar-meli?limit=100"
      );
      setStatus(`✅ Importação concluída: ${data.importados} produtos em ${data.tempo_execucao}.`);
      if (onFinish) onFinish();
    } catch (err: any) {
      setStatus(`❌ Erro: ${String(err?.message || err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Button onClick={handleImport} loading={loading}>
        {loading ? "Importando..." : "📦 Baixar Produtos (Mercado Livre)"}
      </Button>
      {status && <StatusBox>{status}</StatusBox>}
    </div>
  );
}