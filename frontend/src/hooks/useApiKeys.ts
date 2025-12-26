/**
 * Hook personnalisé pour la gestion des clés API
 * Utilise React Query pour le CRUD avec cache
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { ApiKeyInfo, ApiKeyCreate, ApiKeyResponse } from "@/types/api";

// ===== Query Keys =====

export const apiKeysQueryKey = ["api-keys"] as const;

// ===== Types =====

interface UseApiKeysOptions {
  masterKey: string;
  enabled?: boolean;
}

interface CreateApiKeyData extends ApiKeyCreate {
  masterKey: string;
}

interface RevokeApiKeyData {
  keyId: string;
  masterKey: string;
}

// ===== List API Keys =====

export function useApiKeys(options: UseApiKeysOptions) {
  return useQuery({
    queryKey: [...apiKeysQueryKey, options.masterKey],
    queryFn: async () => {
      const result = await api.listApiKeys(options.masterKey);
      return result;
    },
    enabled: options.enabled !== false && !!options.masterKey,
    staleTime: 30000, // 30 secondes
    retry: 1,
  });
}

// ===== Create API Key =====

export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateApiKeyData): Promise<ApiKeyResponse> => {
      const { masterKey, ...keyData } = data;
      return api.createApiKey(keyData, masterKey);
    },
    onMutate: () => {
      return {
        toastId: toast.loading("Création de la clé..."),
      };
    },
    onSuccess: (data, variables, context) => {
      toast.success("Clé API créée", {
        id: context?.toastId,
        description: `La clé "${variables.name}" a été créée avec succès`,
      });

      // Invalider le cache des clés
      queryClient.invalidateQueries({ queryKey: apiKeysQueryKey });
    },
    onError: (error, _variables, context) => {
      toast.error("Échec de la création", {
        id: context?.toastId,
        description: error instanceof Error ? error.message : "Impossible de créer la clé API",
      });
    },
  });
}

// ===== Revoke API Key =====

export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: RevokeApiKeyData): Promise<void> => {
      await api.revokeApiKey(data.keyId, data.masterKey);
    },
    onMutate: () => {
      return {
        toastId: toast.loading("Révocation de la clé..."),
      };
    },
    onSuccess: (_data, _variables, context) => {
      toast.success("Clé révoquée", {
        id: context?.toastId,
        description: "La clé API a été révoquée avec succès",
      });

      // Invalider le cache des clés
      queryClient.invalidateQueries({ queryKey: apiKeysQueryKey });
    },
    onError: (error, _variables, context) => {
      toast.error("Échec de la révocation", {
        id: context?.toastId,
        description: error instanceof Error ? error.message : "Impossible de révoquer la clé",
      });
    },
  });
}

// ===== Combined Hook =====

/**
 * Hook combiné pour la gestion complète des clés API
 */
export function useApiKeysManager(masterKey: string) {
  const keysQuery = useApiKeys({ masterKey, enabled: !!masterKey });
  const createMutation = useCreateApiKey();
  const revokeMutation = useRevokeApiKey();

  return {
    // Data
    keys: keysQuery.data?.keys ?? [],
    total: keysQuery.data?.total ?? 0,
    
    // Loading states
    isLoading: keysQuery.isLoading,
    isCreating: createMutation.isPending,
    isRevoking: revokeMutation.isPending,
    
    // Actions
    createKey: (data: ApiKeyCreate) => 
      createMutation.mutateAsync({ ...data, masterKey }),
    revokeKey: (keyId: string) => 
      revokeMutation.mutateAsync({ keyId, masterKey }),
    refresh: () => keysQuery.refetch(),
    
    // Status
    error: keysQuery.error,
    isError: keysQuery.isError,
  };
}
