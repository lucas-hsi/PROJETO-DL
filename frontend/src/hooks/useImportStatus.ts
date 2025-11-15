"use client";
import { useEffect, useState } from "react";

export function useImportStatus(interval = 10000) {
  const [status, setStatus] = useState<any>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/estoque/meli/status`, { cache: "no-store" });
        if (res.ok) setStatus(await res.json());
      } catch {}
    };
    fetchStatus();
    const timer = setInterval(fetchStatus, interval);
    return () => clearInterval(timer);
  }, [API_URL, interval]);

  return status;
}