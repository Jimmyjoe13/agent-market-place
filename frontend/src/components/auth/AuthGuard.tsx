"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
  fallbackUrl?: string;
}

/**
 * AuthGuard - Protection client-side des routes
 * 
 * Vérifie la présence d'une session active et redirige
 * vers la page spécifiée si non authentifié.
 */
export function AuthGuard({ children, fallbackUrl = "/" }: AuthGuardProps) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Ne pas rediriger pendant le chargement
    if (loading) return;
    
    // Rediriger si pas de session
    if (!session) {
      console.log("[AuthGuard] No session, redirecting to:", fallbackUrl);
      router.replace(fallbackUrl);
    }
  }, [session, loading, router, fallbackUrl]);

  // Afficher un loader pendant la vérification
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Chargement...</p>
        </div>
      </div>
    );
  }

  // Ne rien afficher si pas de session (redirection en cours)
  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Redirection...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

export default AuthGuard;
