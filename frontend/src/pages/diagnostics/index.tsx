import { useState } from "react";
import styled from "styled-components";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { apiGet } from "@/lib/api";

const Wrap = styled.div`
  padding: 24px;
`;

export default function Diagnostics() {
  const [config, setConfig] = useState<any>(null);
  const [whoami, setWhoami] = useState<any>(null);
  const [sample, setSample] = useState<any>(null);

  const loadConfig = async () => {
    const data = await apiGet<any>("/diagnostics/meli/config");
    setConfig(data);
  };

  const loadWhoami = async () => {
    const data = await apiGet<any>("/diagnostics/meli/whoami");
    setWhoami(data);
  };

  const loadSample = async () => {
    const data = await apiGet<any>("/diagnostics/meli/items-sample?limit=5");
    setSample(data);
  };

  return (
    <Wrap>
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Diagnóstico Mercado Livre</CardTitle>
            <CardDescription>Ferramentas de verificação de credenciais e listagem</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <Button onClick={loadWhoami}>Quem sou eu no ML</Button>
            <Button onClick={loadSample}>Amostra Itens Ativos</Button>
            <Button variant="secondary" onClick={loadConfig}>Config</Button>
          </div>
          <div style={{ display: 'grid', gap: 12 }}>
            {config && (<pre style={{ background: '#fafafa', padding: 12 }}>{JSON.stringify(config, null, 2)}</pre>)}
            {whoami && (<pre style={{ background: '#fafafa', padding: 12 }}>{JSON.stringify(whoami, null, 2)}</pre>)}
            {sample && (<pre style={{ background: '#fafafa', padding: 12 }}>{JSON.stringify(sample, null, 2)}</pre>)}
          </div>
        </CardContent>
      </Card>
    </Wrap>
  );
}