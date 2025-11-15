import React, { useState } from "react";
import styled from "styled-components";
import { colors, radius, shadows, typography } from "@/styles/tokens";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const Container = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${colors.background};
`;

const Card = styled.div`
  width: 100%;
  max-width: 420px;
  background: ${colors.card};
  backdrop-filter: blur(16px);
  border: 1px solid ${colors.border};
  border-radius: ${radius.lg};
  box-shadow: ${shadows.base};
  padding: 24px;
`;

const Title = styled.h2`
  font-size: 22px;
  font-weight: ${typography.weightSemibold};
  color: ${colors.textDark};
  margin-bottom: 8px;
`;

const Subtitle = styled.p`
  font-size: 13px;
  color: ${colors.textLight};
  margin-bottom: 16px;
`;

const ErrorBox = styled.pre`
  color: #ef4444;
  font-size: 12px;
  margin: 8px 0 0;
`;

export default function LoginPage() {
  const [email, setEmail] = useState("vendedor@dl.com");
  const [senha, setSenha] = useState("123456");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });
      if (!res.ok) throw new Error(`Login falhou: ${res.status}`);
      const data = await res.json();
      if (typeof window !== "undefined") {
        localStorage.setItem("token", data.access_token);
        const role = String(data.role || "");
        if (role === "vendedor") window.location.href = "/vendedores/estoque";
        else if (role === "anunciador") window.location.href = "/anunciador/estoque";
        else if (role === "gestor") window.location.href = "/gestor/dashboard";
        else window.location.href = "/vendedores/estoque";
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container>
      <Card>
        <Title>Bem-vindo</Title>
        <Subtitle>Faça login para acessar seu painel</Subtitle>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
          <Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@empresa.com" />
          <Input label="Senha" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="••••••" />
          {error && <ErrorBox>{error}</ErrorBox>}
          <Button type="submit" disabled={loading}>
            {loading ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      </Card>
    </Container>
  );
}
