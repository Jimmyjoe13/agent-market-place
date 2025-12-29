import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
interface BudgetLimits {
  max_monthly_tokens: number;
  max_daily_requests: number;
  tokens_used_this_month: number;
  requests_today: number;
  system_prompt_max_length: number;
  usage_percent: number;
}

interface UsageStats {
  key_id: string;
  agent_name?: string;
  tokens_used_this_month: number;
  max_monthly_tokens: number;
  requests_today: number;
  max_daily_requests: number;
  rate_limit_stats: Record<string, number>;
  usage_reset_month?: string;
  daily_reset_date?: string;
}

interface KeyRotateResponse {
  new_key: string;
  key_id: string;
  rotated_at: string;
  warning: string;
}

interface BudgetLimitsUpdate {
  max_monthly_tokens?: number;
  max_daily_requests?: number;
  system_prompt_max_length?: number;
}

/**
 * Hook pour récupérer les limites de budget d'une clé.
 */
export function useBudgetLimits(keyId: string, apiKey: string) {
  return useQuery<BudgetLimits>({
    queryKey: ["budget-limits", keyId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys/${keyId}/budget`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error("Impossible de récupérer les limites");
      }

      return response.json();
    },
    enabled: !!keyId && !!apiKey,
  });
}

/**
 * Hook pour mettre à jour les limites de budget.
 */
export function useUpdateBudgetLimits(keyId: string, apiKey: string) {
  const queryClient = useQueryClient();

  return useMutation<BudgetLimits, Error, BudgetLimitsUpdate>({
    mutationFn: async (limits) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys/${keyId}/budget`, {
        method: "PATCH",
        headers: {
          "X-API-Key": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(limits),
      });

      if (!response.ok) {
        throw new Error("Impossible de mettre à jour les limites");
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budget-limits", keyId] });
    },
  });
}

/**
 * Hook pour récupérer les stats d'utilisation.
 */
export function useUsageStats(keyId: string, apiKey: string) {
  return useQuery<UsageStats>({
    queryKey: ["usage-stats", keyId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys/${keyId}/usage`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error("Impossible de récupérer les stats");
      }

      return response.json();
    },
    enabled: !!keyId && !!apiKey,
    refetchInterval: 30000, // Actualiser toutes les 30s
  });
}

/**
 * Hook pour faire une rotation de clé.
 */
export function useRotateKey(apiKey: string) {
  const queryClient = useQueryClient();

  return useMutation<KeyRotateResponse, Error, string>({
    mutationFn: async (keyId) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys/${keyId}/rotate`, {
        method: "POST",
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error("Impossible de faire la rotation");
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalider toutes les queries liées aux clés
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}

export default useBudgetLimits;
