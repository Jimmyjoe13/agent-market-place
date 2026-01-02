/**
 * useRealtimeUsage Hook
 * =====================
 * 
 * Hook pour récupérer l'usage utilisateur en TEMPS RÉEL via Supabase Realtime.
 * 
 * Fonctionnalités:
 * - Souscription aux changements sur usage_records
 * - Fallback polling si Realtime échoue
 * - Indicateur de connexion (connected/connecting/disconnected)
 * - Auto-reconnexion
 * 
 * Usage:
 *   const { usage, connectionStatus, lastUpdated } = useRealtimeUsage();
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RealtimeChannel, RealtimePostgresChangesPayload } from "@supabase/supabase-js";
import { getSupabaseBrowserClient } from "@/lib/supabase";
import { useAuth } from "./useAuth";
import { api } from "@/lib/api";

// ===== Types =====

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

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

export interface RealtimeUsageResult {
  usage: UserUsage | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  connectionStatus: ConnectionStatus;
  lastUpdated: Date | null;
  refetch: () => Promise<void>;
}

// ===== Utility Functions =====

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

// ===== Hook =====

interface UseRealtimeUsageOptions {
  /** Intervalle de fallback polling en ms (défaut: 30000) */
  fallbackPollingInterval?: number;
  /** Activer le mode debug */
  debug?: boolean;
}

export function useRealtimeUsage(
  options: UseRealtimeUsageOptions = {}
): RealtimeUsageResult {
  const { fallbackPollingInterval = 30000, debug = false } = options;
  
  const { session, user } = useAuth();
  const accessToken = session?.access_token;
  const userId = user?.id;
  
  const queryClient = useQueryClient();
  const supabase = getSupabaseBrowserClient();
  
  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const channelRef = useRef<RealtimeChannel | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Log helper
  const log = useCallback((...args: unknown[]) => {
    if (debug) {
      console.log("[useRealtimeUsage]", ...args);
    }
  }, [debug]);

  // Fetch usage data from API
  const fetchUsage = useCallback(async (): Promise<UserUsage> => {
    if (!accessToken) {
      throw new Error("Non authentifié");
    }
    
    api.setAccessToken(accessToken);
    const data = await api.getUserUsage();
    setLastUpdated(new Date());
    return data;
  }, [accessToken]);

  // React Query for initial fetch and fallback
  const {
    data: usage,
    isLoading,
    isError,
    error,
    refetch: queryRefetch,
  } = useQuery<UserUsage>({
    queryKey: ["user-usage-realtime", userId],
    queryFn: fetchUsage,
    enabled: !!accessToken && !!userId,
    // Polling seulement si Realtime n'est pas connecté
    refetchInterval: connectionStatus !== "connected" ? fallbackPollingInterval : false,
    staleTime: 5000,
  });

  // Refetch wrapper
  const refetch = useCallback(async () => {
    await queryRefetch();
  }, [queryRefetch]);

  // Handle realtime update
  const handleRealtimeUpdate = useCallback(
    (payload: RealtimePostgresChangesPayload<{ [key: string]: unknown }>) => {
      log("Realtime update received:", payload);
      
      // Invalider le cache pour refetch les données complètes
      queryClient.invalidateQueries({ queryKey: ["user-usage-realtime", userId] });
      setLastUpdated(new Date());
    },
    [queryClient, userId, log]
  );

  // Setup Supabase Realtime subscription
  useEffect(() => {
    if (!userId || !accessToken) {
      log("No user or token, skipping realtime setup");
      return;
    }

    log("Setting up realtime subscription for user:", userId);
    setConnectionStatus("connecting");

    // Créer le channel pour écouter les changements sur usage_records
    const channel = supabase
      .channel(`usage-${userId}`)
      .on(
        "postgres_changes",
        {
          event: "*", // INSERT, UPDATE, DELETE
          schema: "public",
          table: "usage_records",
          filter: `user_id=eq.${userId}`,
        },
        handleRealtimeUpdate
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "api_keys",
          filter: `user_id=eq.${userId}`,
        },
        handleRealtimeUpdate
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "documents",
          filter: `user_id=eq.${userId}`,
        },
        handleRealtimeUpdate
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "agents",
          filter: `user_id=eq.${userId}`,
        },
        handleRealtimeUpdate
      );

    // Subscribe with status callback
    channel.subscribe((status: string) => {
      log("Channel status:", status);
      
      if (status === "SUBSCRIBED") {
        setConnectionStatus("connected");
        log("Realtime connected successfully");
      } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
        setConnectionStatus("disconnected");
        log("Realtime error, falling back to polling");
        
        // Auto-reconnect après 5 secondes
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          log("Attempting reconnection...");
          channel.subscribe();
        }, 5000);
      } else if (status === "CLOSED") {
        setConnectionStatus("disconnected");
      }
    });

    channelRef.current = channel;

    // Cleanup
    return () => {
      log("Cleaning up realtime subscription");
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
      setConnectionStatus("disconnected");
    };
  }, [userId, accessToken, supabase, handleRealtimeUpdate, log]);

  return {
    usage: usage ?? null,
    isLoading,
    isError,
    error: error as Error | null,
    connectionStatus,
    lastUpdated,
    refetch,
  };
}

export default useRealtimeUsage;
