import React, { useMemo } from "react";
import jwt from "jsonwebtoken";
import { useRouter } from "next/router";

export default function AppHeader() {
  const router = useRouter();
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const role = useMemo(() => {
    if (!token) return null;
    try {
      const dec: any = jwt.decode(token);
      return dec?.role || null;
    } catch {
      return null;
    }
  }, [token]);

  const sair = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      router.push("/login");
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 12, borderBottom: "1px solid #eee" }}>
      <div>DL Auto Peças</div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <span>Role: {role || "-"}</span>
        <button onClick={sair} style={{ padding: "6px 12px" }}>Sair</button>
      </div>
    </div>
  );
}
