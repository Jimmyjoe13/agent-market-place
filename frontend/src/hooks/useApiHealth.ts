/**
 * Hook personnalisé pour le status de l'API
 * Utilise React Query pour le polling automatique et le caching
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ApiHealthData {
  status: "healthy" | "unhealthy";
  version: string;
}

export function useApiHealth(options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({
    queryKey: ["api-health"],
    queryFn: async (): Promise<ApiHealthData> => {
      const health = await api.healthCheck();
      return {
        status: health.status as "healthy" | "unhealthy",
        version: health.version,
      };
    },
    refetchInterval: options?.refetchInterval ?? 30000, // 30 secondes par défaut
    retry: 1,
    enabled: options?.enabled ?? true,
    staleTime: 10000, // Considéré comme frais pendant 10 secondes
  });
}

/**
 * Hook helper pour obtenir directement le status
 */
export function useApiStatus() {
  const { data, isLoading, isError, refetch, isFetching } = useApiHealth();

  const status = isLoading
    ? "loading"
    : isError
    ? "offline"
    : data?.status === "healthy"
    ? "online"
    : "offline";

  return {
    status,
    version: data?.version,
    isLoading,
    isFetching,
    refetch,
  };
}
