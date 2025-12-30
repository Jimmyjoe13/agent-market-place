/**
 * Hook personnalisé pour la gestion de la configuration agent
 * Utilise React Query pour le cache et la synchronisation
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// Types
export interface AgentConfig {
  model_id: string;
  system_prompt: string | null;
  rag_enabled: boolean;
  agent_name: string | null;
}

export interface AgentConfigResponse {
  agent_id: string;
  config: AgentConfig;
}

export interface AgentConfigUpdate {
  model_id?: string;
  system_prompt?: string;
  rag_enabled?: boolean;
  agent_name?: string;
}

export interface LLMModel {
  id: string;
  provider: string;
  name: string;
  description?: string;
  recommended?: boolean;
  premium?: boolean;
  new?: boolean;
}

// Query keys
const QUERY_KEYS = {
  agentConfig: ['agent-config'] as const,
  availableModels: ['available-models'] as const,
};

/**
 * Hook pour récupérer la configuration agent courante
 */
export function useAgentConfig() {
  return useQuery({
    queryKey: QUERY_KEYS.agentConfig,
    queryFn: async () => {
      const response = await api.getAgentConfig();
      return response;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: 1,
  });
}

/**
 * Hook pour récupérer la liste des modèles LLM disponibles
 */
export function useAvailableModels() {
  return useQuery({
    queryKey: QUERY_KEYS.availableModels,
    queryFn: async () => {
      const response = await api.getAvailableModels();
      return response.models;
    },
    staleTime: 1000 * 60 * 30, // 30 minutes (liste statique)
  });
}

/**
 * Hook pour mettre à jour la configuration agent
 */
export function useUpdateAgentConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (config: AgentConfigUpdate) => {
      const response = await api.updateAgentConfig(config);
      return response;
    },
    onSuccess: (data) => {
      // Invalider le cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentConfig });
      toast.success('Configuration mise à jour');
    },
    onError: (error: any) => {
      const message = error?.response?.data?.message || 'Échec de la mise à jour';
      toast.error(message);
    },
  });
}

/**
 * Hook combiné pour la gestion complète de la config agent
 */
export function useAgentConfigManager() {
  const configQuery = useAgentConfig();
  const modelsQuery = useAvailableModels();
  const updateMutation = useUpdateAgentConfig();

  return {
    // Data
    config: configQuery.data?.config,
    agentId: configQuery.data?.agent_id,
    models: modelsQuery.data || [],
    
    // States
    isLoading: configQuery.isLoading || modelsQuery.isLoading,
    isUpdating: updateMutation.isPending,
    error: configQuery.error || modelsQuery.error,
    
    // Actions
    updateConfig: updateMutation.mutate,
    updateConfigAsync: updateMutation.mutateAsync,
    refetch: configQuery.refetch,
  };
}

export default useAgentConfigManager;
