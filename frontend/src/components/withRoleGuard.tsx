import React, { useEffect } from "react";
import { useRouter } from "next/router";
import { getToken, parseRoleFromToken } from "@/utils/auth";

export default function withRoleGuard<P extends object>(Component: React.ComponentType<P>, opts: { allowedRoles: string[] }) {
  return function Guarded(props: P) {
    const router = useRouter();
    useEffect(() => {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      const role = parseRoleFromToken(token);
      if (!role || !opts.allowedRoles.includes(role)) {
        router.replace("/login");
      }
    }, [router]);
    return <Component {...props} />;
  };
}
