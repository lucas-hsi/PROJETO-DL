import React, { useEffect, useState } from "react";
import { getHealth } from "../lib/api";
import { HealthCard } from "../components/HealthCard";

export default function HomePage() {
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "system-ui, Arial" }}>
      <h1>DL Auto Peças</h1>
      <p>API Online</p>
      {error && <pre style={{ color: "red" }}>{error}</pre>}
      <HealthCard health={health} />
    </div>
  );
}