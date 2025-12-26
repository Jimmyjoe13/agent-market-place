/**
 * NextAuth.js Configuration
 * ===========================
 * 
 * Configuration de l'authentification OAuth avec Google.
 * Intégration avec le backend FastAPI pour la gestion des utilisateurs.
 */

import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { NextAuthConfig } from "next-auth";

// Configuration NextAuth
export const authConfig: NextAuthConfig = {
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      // Forcer l'affichage du sélecteur de compte
      authorization: {
        params: {
          prompt: "select_account",
        },
      },
    }),
  ],
  // Secret obligatoire pour NextAuth v5
  secret: process.env.AUTH_SECRET,
  
  // Configuration de confiance pour le proxy Netlify
  trustHost: true,
  
  callbacks: {
    // Callback de vérification d'autorisation (pour le middleware)
    authorized({ auth, request }) {
      const isLoggedIn = !!auth?.user;
      const { pathname } = request.nextUrl;
      
      // Routes publiques
      const publicRoutes = ["/", "/login", "/register", "/docs", "/subscription", "/privacy", "/terms"];
      const isPublicRoute = publicRoutes.some(
        (route) => pathname === route || pathname.startsWith(`${route}/`)
      );
      
      // API routes gérées par le backend
      const isApiRoute = pathname.startsWith("/api");
      
      // Autoriser les routes publiques et API
      if (isPublicRoute || isApiRoute) {
        return true;
      }
      
      // Exiger l'auth pour les autres routes
      return isLoggedIn;
    },
    
    // Callback après authentification réussie
    async signIn({ user, account }) {
      if (!user.email) {
        console.error("[Auth] No email provided by OAuth provider");
        return false;
      }

      try {
        // Envoyer les infos au backend pour créer/mettre à jour l'utilisateur
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        
        console.log("[Auth] Syncing user with backend:", user.email);
        
        const response = await fetch(`${backendUrl}/auth/callback/google`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            code: account?.access_token,
            provider: "google",
            email: user.email,
            name: user.name,
            avatar_url: user.image,
            provider_id: account?.providerAccountId,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error("[Auth] Backend sync failed:", response.status, errorText);
          // Continuer quand même - le backend créera l'utilisateur plus tard
        } else {
          const data = await response.json();
          console.log("[Auth] Backend sync successful:", data.user?.id);
          
          // Stocker l'ID utilisateur pour les requêtes ultérieures
          if (data.user?.id) {
            (user as any).backendUserId = data.user.id;
            (user as any).plan = data.user.plan_slug || "free";
          }
        }

        return true;
      } catch (error) {
        console.error("[Auth] Error syncing with backend:", error);
        // Autoriser quand même la connexion - le frontend gèrera l'erreur
        return true;
      }
    },

    // Enrichir le JWT avec les infos utilisateur
    async jwt({ token, user, account }) {
      if (user) {
        token.id = (user as any).backendUserId || user.id;
        token.plan = (user as any).plan || "free";
        token.accessToken = account?.access_token;
      }
      return token;
    },

    // Enrichir la session avec les infos du token
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
        (session.user as any).plan = token.plan;
        (session as any).accessToken = token.accessToken;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
  },
  debug: process.env.NODE_ENV === "development",
};

// Export handlers et fonctions
export const { handlers, signIn, signOut, auth } = NextAuth(authConfig);
