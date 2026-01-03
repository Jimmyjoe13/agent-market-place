/**
 * Hook pour la gestion des agents (Multi-Agent)
 * Gère le listing, la sélection et les opérations CRUD
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { AgentInfo, AgentCreate, AgentUpdate } from '@/types/api';

// Clés de cache React Query
const QUERY_KEYS = {
  agents: ['agents'] as const,
  agent: (id: string) => ['agents', id] as const,
  agentKeys: (id: string) => ['agents', id, 'keys'] as const,
};

export function useAgents(activeAgentId?: string) {
  const queryClient = useQueryClient();

  // 1. Récupérer la liste des agents
  const { 
    data: response, 
    isLoading: isLoadingList, 
    error: listError 
  } = useQuery({
    queryKey: QUERY_KEYS.agents,
    queryFn: async () => {
      const res = await api.getAgents();
      return res;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const agents = response?.agents || [];
  
  // 3. Récupérer les détails de l'agent sélectionné
  const selectedAgent = activeAgentId ? agents.find(a => a.id === activeAgentId) || null : null;

  // 4. Mutations
  
  // Créer un agent (Note: dans architecture v3, les agents sont créés via les clés API)
  const createMutation = useMutation({
    mutationFn: async (newAgent: AgentCreate) => {
      return await api.createAgent(newAgent);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      toast.success('Agent créé avec succès');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail?.message || 'Erreur lors de la création');
    }
  });

  // Mettre à jour un agent
  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string, updates: AgentUpdate }) => 
      api.updateAgent(id, updates),
    onSuccess: (updatedAgent) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      queryClient.setQueryData(QUERY_KEYS.agent(updatedAgent.id), updatedAgent);
      toast.success('Agent mis à jour');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail?.message || 'Erreur de mise à jour');
    }
  });

  // Supprimer un agent
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteAgent(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      toast.success('Agent supprimé');
    },
    onError: (err: any) => {
      toast.error('Erreur lors de la suppression');
    }
  });

  // Récupérer les clés API de l'agent sélectionné
  const { data: keysResponse, isLoading: isLoadingKeys } = useQuery({
    queryKey: QUERY_KEYS.agentKeys(activeAgentId || ''),
    queryFn: () => api.getAgentKeys(activeAgentId!),
    enabled: !!activeAgentId,
  });

  // Prendre la clé active, ou la première disponible (fallback), ou undefined
  const activeKey = keysResponse?.keys?.find?.((k: any) => k.is_active) || keysResponse?.keys?.[0];

  return {
    // Data
    agents,
    selectedAgent,
    activeKey,
    
    // Status
    isLoading: isLoadingList || (!!activeAgentId && isLoadingKeys),
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    
    // Actions
    createAgent: createMutation.mutateAsync,
    updateAgent: updateMutation.mutateAsync,
    deleteAgent: deleteMutation.mutateAsync,
  };
}
