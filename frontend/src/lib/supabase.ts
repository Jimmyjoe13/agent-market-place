/**
 * Supabase Client Configuration
 * ==============================
 *
 * Configuration des clients Supabase pour browser et server.
 * Remplace NextAuth.js pour l'authentification.
 */

import { createBrowserClient } from "@supabase/ssr";

// Variables d'environnement Supabase
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/**
 * Client Supabase pour le browser (côté client).
 *
 * Utilise les cookies pour persister la session.
 */
export function createClient() {
  return createBrowserClient(supabaseUrl, supabaseAnonKey);
}

/**
 * Client Supabase singleton pour les composants client.
 */
let browserClient: ReturnType<typeof createBrowserClient> | null = null;

export function getSupabaseBrowserClient() {
  if (!browserClient) {
    browserClient = createClient();
  }
  return browserClient;
}
