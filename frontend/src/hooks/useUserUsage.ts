/**
 * Hook pour récupérer l'usage global de l'utilisateur
 * =====================================================
 * 
 * Récupère les statistiques d'utilisation mensuelles :
 * - Requêtes utilisées/limite
 * - Documents/limite
 * - Clés API/limite
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./useAuth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface UserUsage {
  // Usage courant
  requests_count: number;
  documents_count: number;
  api_keys_count: number;
  agents_count?: number;
  tokens_used?: number;
  
  // Limites du plan
  requests_limit: number;
  documents_limit: number;
  api_keys_limit: number;
  agents_limit?: number;
  
  // Plan info
  plan: string;
  subscription_status: string;
  period?: string;
}

export interface UsagePercentages {
  requests: number;
  documents: number;
  apiKeys: number;
  agents: number;
}

/**
 * Calcule les pourcentages d'utilisation.
 */
export function calculateUsagePercentages(usage: UserUsage): UsagePercentages {
  const safePercent = (used: number, limit: number) => {
    if (limit <= 0 || limit === -1) return 0; // -1 = unlimited
    return Math.min(Math.round((used / limit) * 100), 100);
  };

  return {
    requests: safePercent(usage.requests_count, usage.requests_limit),
    documents: safePercent(usage.documents_count, usage.documents_limit),
    apiKeys: safePercent(usage.api_keys_count, usage.api_keys_limit),
    agents: safePercent(usage.agents_count || 0, usage.agents_limit || 1),
  };
}

/**
 * Détermine la couleur en fonction du pourcentage.
 */
export function getUsageColor(percent: number): string {
  if (percent >= 90) return "text-red-500";
  if (percent >= 75) return "text-amber-500";
  if (percent >= 50) return "text-yellow-500";
  return "text-green-500";
}

/**
 * Détermine la couleur de la barre de progression.
 */
export function getProgressColor(percent: number): string {
  if (percent >= 90) return "bg-red-500";
  if (percent >= 75) return "bg-amber-500";
  if (percent >= 50) return "bg-yellow-500";
  return "bg-green-500";
}

/**
 * Hook principal pour récupérer l'usage utilisateur.
 */
export function useUserUsage(options?: { refetchInterval?: number }) {
  const { session } = useAuth();
  const accessToken = session?.access_token;

  return useQuery<UserUsage>({
    queryKey: ["user-usage"],
    queryFn: async () => {
      if (!accessToken) {
        throw new Error("Non authentifié");
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/console/usage`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Impossible de récupérer l'usage");
      }

      return response.json();
    },
    enabled: !!accessToken,
    refetchInterval: options?.refetchInterval ?? 30000, // 30 secondes par défaut
    staleTime: 10000, // Considérer frais pendant 10s
  });
}

export default useUserUsage;
