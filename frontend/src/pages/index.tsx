import { useRouter } from 'next/router';
import { useEffect } from 'react';

export default function Index() {
  const router = useRouter();

  useEffect(() => {
    // Redirecionar para página de login ou dashboard
    router.push('/login');
  }, [router]);

  return null;
}