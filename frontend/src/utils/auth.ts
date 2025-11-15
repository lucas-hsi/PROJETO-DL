import jwt from "jsonwebtoken";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function parseRoleFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const dec: any = jwt.decode(token);
    return dec?.role || null;
  } catch {
    return null;
  }
}
