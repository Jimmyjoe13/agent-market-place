/**
 * Page de gestion des clés API (Self-Service)
 * ============================================
 *
 * Interface utilisateur pour créer et gérer ses clés API.
 * Utilise Supabase Auth pour l'authentification.
 */

"use client";

import { useAuth } from "@/hooks/useAuth";
import { redirect } from "next/navigation";
import { ApiKeyManager } from "@/components/console/ApiKeyManager";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle, Key } from "lucide-react";

export default function KeysPage() {
  const { isAuthenticated, loading } = useAuth();

  // Rediriger vers login si non authentifié
  if (!loading && !isAuthenticated) {
    redirect("/login");
  }

  // Loading state
  if (loading) {
    return (
      <div className="h-full overflow-y-auto p-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-8">
            <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse" />
            <div className="h-4 w-72 bg-zinc-800 rounded animate-pulse mt-2" />
          </div>
          <Card className="border-zinc-800 bg-zinc-900/50">
            <CardContent className="py-12">
              <div className="flex items-center justify-center">
                <Key className="h-6 w-6 animate-pulse text-zinc-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Clés API</h1>
          <p className="text-zinc-400 mt-1">
            Créez et gérez vos clés d&apos;accès à l&apos;API RAG Agent.
          </p>
        </div>

        {/* Info Card */}
        <Card className="mb-6 border-indigo-500/20 bg-indigo-500/5">
          <CardContent className="flex items-start gap-4 pt-6">
            <AlertCircle className="h-5 w-5 shrink-0 text-indigo-400" />
            <div className="text-sm">
              <p className="mb-2 font-medium text-indigo-300">
                À propos des clés API
              </p>
              <p className="text-indigo-400/80">
                Vos clés API permettent d&apos;authentifier vos applications auprès de l&apos;API.
                Chaque clé dispose de permissions spécifiques (query, feedback, ingest).
                Ne partagez jamais vos clés et révoque-les immédiatement si elles sont compromises.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* API Key Manager */}
        <div data-tour="api-keys">
          <ApiKeyManager />
        </div>

        {/* Usage Example */}
        <Card className="mt-6 border-zinc-800 bg-zinc-900/50">
          <CardContent className="pt-6">
            <h3 className="font-medium text-zinc-200 mb-3">Exemple d&apos;utilisation</h3>
            <pre className="rounded-lg bg-zinc-950 p-4 text-sm overflow-x-auto">
              <code className="text-zinc-300">
{`curl -X POST https://api.rag-agent.com/api/v1/query \\
  -H "X-API-Key: sk-proj-votre_cle_ici" \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Quelles sont mes compétences?"}'`}
              </code>
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
