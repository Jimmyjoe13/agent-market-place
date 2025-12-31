/**
 * Login Form Component
 * =====================
 *
 * Formulaire de connexion avec OAuth (Google, GitHub, Microsoft) et Email/Password.
 * Utilise Supabase Auth.
 */

"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";

type AuthMethod = "google" | "github" | "microsoft" | "email";

export function LoginForm() {
  const [isLoading, setIsLoading] = useState<AuthMethod | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showEmailForm, setShowEmailForm] = useState(false);

  const { signInWithGoogle, signInWithGithub, signInWithMicrosoft, signInWithEmail } = useAuth();

  const handleOAuthLogin = async (provider: "google" | "github" | "microsoft") => {
    try {
      setIsLoading(provider);
      setError(null);

      switch (provider) {
        case "google":
          await signInWithGoogle();
          break;
        case "github":
          await signInWithGithub();
          break;
        case "microsoft":
          await signInWithMicrosoft();
          break;
      }
    } catch (err) {
      setError("Une erreur est survenue. Veuillez réessayer.");
      setIsLoading(null);
    }
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoading("email");
      setError(null);

      const { error: authError } = await signInWithEmail(email, password);
      
      if (authError) {
        setError(authError.message);
      }
    } catch (err) {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setIsLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Error message */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
          {error}
        </div>
      )}

      {/* OAuth Buttons */}
      <div className="space-y-3">
        {/* Google */}
        <button
          onClick={() => handleOAuthLogin("google")}
          disabled={isLoading !== null}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-white text-gray-900 font-medium rounded-lg hover:bg-gray-100 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
        >
          {isLoading === "google" ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
          )}
          <span>{isLoading === "google" ? "Connexion..." : "Continuer avec Google"}</span>
        </button>

        {/* GitHub */}
        <button
          onClick={() => handleOAuthLogin("github")}
          disabled={isLoading !== null}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700"
        >
          {isLoading === "github" ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
          )}
          <span>{isLoading === "github" ? "Connexion..." : "Continuer avec GitHub"}</span>
        </button>

        {/* Microsoft */}
        <button
          onClick={() => handleOAuthLogin("microsoft")}
          disabled={isLoading !== null}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-[#2F2F2F] text-white font-medium rounded-lg hover:bg-[#3F3F3F] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700"
        >
          {isLoading === "microsoft" ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 21 21">
              <rect x="1" y="1" width="9" height="9" fill="#f25022" />
              <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
              <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
              <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
            </svg>
          )}
          <span>{isLoading === "microsoft" ? "Connexion..." : "Continuer avec Microsoft"}</span>
        </button>
      </div>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-white/10" />
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="px-2 bg-transparent text-slate-500">ou</span>
        </div>
      </div>

      {/* Email/Password Form */}
      {showEmailForm ? (
        <form onSubmit={handleEmailLogin} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="votre@email.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading !== null}
            className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading === "email" ? (
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            ) : (
              "Se connecter"
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowEmailForm(false)}
            className="w-full text-sm text-slate-400 hover:text-slate-300"
          >
            Retour aux options de connexion
          </button>
        </form>
      ) : (
        <button
          onClick={() => setShowEmailForm(true)}
          className="w-full py-3 bg-slate-800/50 text-slate-300 font-medium rounded-lg hover:bg-slate-700/50 transition-all duration-200 border border-slate-700"
        >
          Continuer avec Email
        </button>
      )}

      {/* Info */}
      <div className="text-center pt-4">
        <p className="text-xs text-slate-500">
          🔒 Vos données sont protégées par chiffrement SSL
        </p>
      </div>
    </div>
  );
}
