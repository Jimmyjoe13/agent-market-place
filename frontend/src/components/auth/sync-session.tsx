"use client";

import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";

/**
 * Synchronise la session Supabase avec le client API.
 * Composant invisible qui met à jour le token d'accès.
 */
export function SyncSession() {
  const { session } = useAuth();

  useEffect(() => {
    if (session?.access_token) {
      api.setAccessToken(session.access_token);
    }
  }, [session]);

  return null;
}
