/**
 * Hook pour la gestion de la mémoire conversationnelle des agents
 * 
 * Permet de:
 * - Récupérer l'historique de mémoire d'un agent
 * - Effacer la mémoire d'un agent
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// Types
export interface MemoryMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface MemoryStats {
  count: number;
  oldest_message: string | null;
  newest_message: string | null;
}

export interface AgentMemoryResponse {
  agent_id: string;
  agent_name: string;
  memory_limit: number;
  messages: MemoryMessage[];
  stats: MemoryStats;
}

// Clés de cache
const QUERY_KEYS = {
  agentMemory: (agentId: string) => ['agents', agentId, 'memory'] as const,
};

export function useAgentMemory(agentId: string | null) {
  const queryClient = useQueryClient();

  // Récupérer la mémoire d'un agent
  const {
    data: memoryData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: agentId ? QUERY_KEYS.agentMemory(agentId) : ['agents', 'memory', 'disabled'],
    queryFn: async (): Promise<AgentMemoryResponse> => {
      if (!agentId) throw new Error('No agent ID');
      return await api.getAgentMemory(agentId);
    },
    enabled: !!agentId,
    staleTime: 1000 * 30, // 30 secondes
    refetchOnWindowFocus: false,
  });

  // Effacer la mémoire
  const clearMutation = useMutation({
    mutationFn: async () => {
      if (!agentId) throw new Error('No agent ID');
      await api.clearAgentMemory(agentId);
    },
    onSuccess: () => {
      // Invalider le cache
      if (agentId) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentMemory(agentId) });
      }
      toast.success('Mémoire effacée', {
        description: 'L\'agent a oublié tout l\'historique de conversation.',
      });
    },
    onError: (error: any) => {
      toast.error('Erreur', {
        description: error?.response?.data?.detail || 'Impossible d\'effacer la mémoire',
      });
    },
  });

  return {
    // Data
    messages: memoryData?.messages || [],
    stats: memoryData?.stats || { count: 0, oldest_message: null, newest_message: null },
    memoryLimit: memoryData?.memory_limit || 20,
    agentName: memoryData?.agent_name || '',

    // Status
    isLoading,
    isClearing: clearMutation.isPending,
    error: error as Error | null,

    // Actions
    clearMemory: clearMutation.mutateAsync,
    refetch,
  };
}

export default useAgentMemory;

