/**
 * Hook personnalisé pour la gestion self-service des clés API
 * Utilise React Query avec session utilisateur (pas de Master Key)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import type { ApiKeyInfo, ApiKeyCreate, ApiKeyResponse } from "@/types/api";

// ===== Query Keys =====

export const userApiKeysQueryKey = ["user-api-keys"] as const;

// ===== Types =====

interface UseUserApiKeysOptions {
  enabled?: boolean;
  includeInactive?: boolean;
}

interface CreateKeyInput extends Omit<ApiKeyCreate, "scopes"> {
  scopes?: string[];
}

// ===== List User API Keys =====

export function useUserApiKeys(options: UseUserApiKeysOptions = {}) {
  const { data: session, status } = useSession();
  const isAuthenticated = status === "authenticated";

  return useQuery({
    queryKey: userApiKeysQueryKey,
    queryFn: async () => {
      // Passer le token d'accès si disponible
      if (session?.accessToken) {
        api.setAccessToken(session.accessToken);
      }
      return api.getUserApiKeys();
    },
    enabled: options.enabled !== false && isAuthenticated,
    staleTime: 30000, // 30 secondes
    retry: 2,
  });
}

// ===== Create User API Key =====

export function useCreateUserApiKey() {
  const queryClient = useQueryClient();
  const { data: session } = useSession();

  return useMutation({
    mutationFn: async (input: CreateKeyInput): Promise<ApiKeyResponse> => {
      if (session?.accessToken) {
        api.setAccessToken(session.accessToken);
      }
      
      const request: ApiKeyCreate = {
        name: input.name,
        scopes: input.scopes || ["query"],
        rate_limit_per_minute: input.rate_limit_per_minute || 100,
        monthly_quota: input.monthly_quota || 0,
        expires_in_days: input.expires_in_days,
        metadata: input.metadata,
      };
      
      return api.createUserApiKey(request);
    },
    onMutate: () => {
      return {
        toastId: toast.loading("Création de la clé..."),
      };
    },
    onSuccess: (data, variables, context) => {
      toast.success("Clé API créée", {
        id: context?.toastId,
        description: `Clé "${variables.name}" créée avec succès`,
      });

      // Invalider le cache des clés
      queryClient.invalidateQueries({ queryKey: userApiKeysQueryKey });
    },
    onError: (error, _variables, context) => {
      const message = error instanceof Error 
        ? error.message 
        : "Impossible de créer la clé API";
      
      toast.error("Échec de la création", {
        id: context?.toastId,
        description: message,
      });
    },
  });
}

// ===== Revoke User API Key =====

export function useRevokeUserApiKey() {
  const queryClient = useQueryClient();
  const { data: session } = useSession();

  return useMutation({
    mutationFn: async (keyId: string): Promise<void> => {
      if (session?.accessToken) {
        api.setAccessToken(session.accessToken);
      }
      await api.revokeUserApiKey(keyId);
    },
    onMutate: () => {
      return {
        toastId: toast.loading("Révocation de la clé..."),
      };
    },
    onSuccess: (_data, _keyId, context) => {
      toast.success("Clé révoquée", {
        id: context?.toastId,
        description: "La clé API a été révoquée avec succès",
      });

      // Invalider le cache des clés
      queryClient.invalidateQueries({ queryKey: userApiKeysQueryKey });
    },
    onError: (error, _keyId, context) => {
      const message = error instanceof Error 
        ? error.message 
        : "Impossible de révoquer la clé";
      
      toast.error("Échec de la révocation", {
        id: context?.toastId,
        description: message,
      });
    },
  });
}

// ===== Combined Hook =====

/**
 * Hook combiné pour la gestion complète des clés API utilisateur
 * Utilise la session NextAuth au lieu de la Master Key
 */
export function useUserApiKeysManager() {
  const keysQuery = useUserApiKeys();
  const createMutation = useCreateUserApiKey();
  const revokeMutation = useRevokeUserApiKey();

  return {
    // Data
    keys: keysQuery.data?.keys ?? [],
    total: keysQuery.data?.total ?? 0,
    
    // Loading states
    isLoading: keysQuery.isLoading,
    isCreating: createMutation.isPending,
    isRevoking: revokeMutation.isPending,
    
    // Actions
    createKey: (input: CreateKeyInput) => createMutation.mutateAsync(input),
    revokeKey: (keyId: string) => revokeMutation.mutateAsync(keyId),
    refresh: () => keysQuery.refetch(),
    
    // Last created key (for modal display)
    lastCreatedKey: createMutation.data,
    resetLastCreatedKey: () => createMutation.reset(),
    
    // Status
    error: keysQuery.error,
    isError: keysQuery.isError,
  };
}
