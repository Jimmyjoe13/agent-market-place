/**
 * useAuth Hook
 * =============
 *
 * Hook d'authentification Supabase remplaçant useSession de NextAuth.
 *
 * Usage:
 *   const { user, session, loading, signInWithGoogle, signOut } = useAuth();
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { User, Session, AuthError } from "@supabase/supabase-js";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type AuthProvider = "google" | "github" | "azure" | "email";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: AuthError | null;
}

interface UseAuthReturn extends AuthState {
  // OAuth Sign In
  signInWithGoogle: () => Promise<void>;
  signInWithGithub: () => Promise<void>;
  signInWithMicrosoft: () => Promise<void>;
  // Email/Password
  signInWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signUpWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  // Sign Out
  signOut: () => Promise<void>;
  // Helpers
  isAuthenticated: boolean;
}

export function useAuth(): UseAuthReturn {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    loading: true,
    error: null,
  });

  const supabase = getSupabaseBrowserClient();

  // Initialiser et écouter les changements d'auth
  useEffect(() => {
    // Récupérer la session initiale
    const getInitialSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) {
          console.error("[useAuth] Error getting session:", error);
          setState(prev => ({ ...prev, loading: false, error }));
          return;
        }

        setState({
          user: session?.user ?? null,
          session,
          loading: false,
          error: null,
        });
      } catch (err) {
        console.error("[useAuth] Unexpected error:", err);
        setState(prev => ({ ...prev, loading: false }));
      }
    };

    getInitialSession();

    // Écouter les changements d'état d'auth
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: string, session: Session | null) => {
        console.log("[useAuth] Auth state changed:", event);
        
        // Gestion de la déconnexion - redirection automatique
        if (event === "SIGNED_OUT") {
          setState({
            user: null,
            session: null,
            loading: false,
            error: null,
          });
          // Rediriger vers la page d'accueil
          if (typeof window !== "undefined") {
            window.location.href = "/";
          }
          return;
        }
        
        setState({
          user: session?.user ?? null,
          session,
          loading: false,
          error: null,
        });

        // Sync avec le backend si nécessaire
        if (event === "SIGNED_IN" && session?.user) {
          await syncUserWithBackend(session);
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  // Sync utilisateur avec le backend (pour créer le profile si nécessaire)
  const syncUserWithBackend = async (session: Session) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      
      await fetch(`${backendUrl}/auth/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          email: session.user.email,
          name: session.user.user_metadata?.full_name || session.user.user_metadata?.name,
          avatar_url: session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture,
          provider: session.user.app_metadata?.provider || "email",
          provider_id: session.user.id,
        }),
      });
    } catch (error) {
      console.error("[useAuth] Backend sync failed:", error);
      // Non bloquant - le trigger Supabase créera le profile
    }
  };

  // OAuth: Google
  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: {
          prompt: "select_account",
        },
      },
    });
    if (error) {
      console.error("[useAuth] Google sign in error:", error);
      setState(prev => ({ ...prev, error }));
    }
  }, [supabase]);

  // OAuth: GitHub
  const signInWithGithub = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      console.error("[useAuth] GitHub sign in error:", error);
      setState(prev => ({ ...prev, error }));
    }
  }, [supabase]);

  // OAuth: Microsoft (Azure)
  const signInWithMicrosoft = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "azure",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        scopes: "email profile openid",
      },
    });
    if (error) {
      console.error("[useAuth] Microsoft sign in error:", error);
      setState(prev => ({ ...prev, error }));
    }
  }, [supabase]);

  // Email/Password: Sign In
  const signInWithEmail = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      console.error("[useAuth] Email sign in error:", error);
      setState(prev => ({ ...prev, error }));
    }
    return { error };
  }, [supabase]);

  // Email/Password: Sign Up
  const signUpWithEmail = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      console.error("[useAuth] Email sign up error:", error);
      setState(prev => ({ ...prev, error }));
    }
    return { error };
  }, [supabase]);

  // Sign Out
  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error("[useAuth] Sign out error:", error);
      setState(prev => ({ ...prev, error }));
    }
  }, [supabase]);

  return {
    ...state,
    signInWithGoogle,
    signInWithGithub,
    signInWithMicrosoft,
    signInWithEmail,
    signUpWithEmail,
    signOut,
    isAuthenticated: !!state.session,
  };
}

/**
 * Hook simplifié pour vérifier si l'utilisateur est connecté.
 */
export function useIsAuthenticated(): boolean {
  const { isAuthenticated } = useAuth();
  return isAuthenticated;
}
