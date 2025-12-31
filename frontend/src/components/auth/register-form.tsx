/**
 * Register Form Component
 * ========================
 *
 * Formulaire d'inscription avec OAuth (Google/GitHub/Microsoft) et Email.
 * Utilise Supabase Auth.
 */

"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Loader2, Github } from "lucide-react";
import Link from "next/link";

type AuthMethod = "google" | "github" | "microsoft" | "email";

interface RegisterFormProps {
  onSuccess?: () => void;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [isLoading, setIsLoading] = useState<AuthMethod | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showEmailForm, setShowEmailForm] = useState(false);

  const { signInWithGoogle, signInWithGithub, signInWithMicrosoft, signUpWithEmail } = useAuth();

  const handleOAuthRegister = async (provider: "google" | "github" | "microsoft") => {
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

  const handleEmailRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }

    try {
      setIsLoading("email");
      setError(null);

      const { error: authError } = await signUpWithEmail(email, password);
      
      if (authError) {
        setError(authError.message);
      } else {
        // Succès - afficher un message de vérification
        setError(null);
        alert("Un email de confirmation a été envoyé. Veuillez vérifier votre boîte mail.");
      }
    } catch (err) {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setIsLoading(null);
    }
  };

  const loadingAny = isLoading !== null;

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
          onClick={() => handleOAuthRegister("google")}
          disabled={loadingAny}
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
          <span>{isLoading === "google" ? "Inscription..." : "S'inscrire avec Google"}</span>
        </button>

        {/* GitHub */}
        <button
          onClick={() => handleOAuthRegister("github")}
          disabled={loadingAny}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-zinc-800 text-white font-medium rounded-lg hover:bg-zinc-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed border border-zinc-700"
        >
          {isLoading === "github" ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Github className="w-5 h-5" />
          )}
          <span>{isLoading === "github" ? "Inscription..." : "S'inscrire avec GitHub"}</span>
        </button>

        {/* Microsoft */}
        <button
          onClick={() => handleOAuthRegister("microsoft")}
          disabled={loadingAny}
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
          <span>{isLoading === "microsoft" ? "Inscription..." : "S'inscrire avec Microsoft"}</span>
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
        <form onSubmit={handleEmailRegister} className="space-y-4">
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
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
              minLength={8}
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Minimum 8 caractères"
            />
          </div>
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1">
              Confirmer le mot de passe
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loadingAny}
            className="w-full py-3 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading === "email" ? (
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            ) : (
              "Créer mon compte"
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowEmailForm(false)}
            className="w-full text-sm text-slate-400 hover:text-slate-300"
          >
            Retour aux options d'inscription
          </button>
        </form>
      ) : (
        <button
          onClick={() => setShowEmailForm(true)}
          className="w-full py-3 bg-slate-800/50 text-slate-300 font-medium rounded-lg hover:bg-slate-700/50 transition-all duration-200 border border-slate-700"
        >
          S'inscrire avec Email
        </button>
      )}

      {/* Features */}
      <div className="space-y-3 text-sm text-slate-400 pt-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <span>Accès instantané à l&apos;API</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <span>100 requêtes/mois gratuites</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <span>Aucune carte bancaire requise</span>
        </div>
      </div>

      {/* Login Link */}
      <div className="text-center pt-4">
        <p className="text-sm text-slate-500">
          Déjà un compte ?{" "}
          <Link href="/login" className="text-purple-400 hover:text-purple-300 transition-colors font-medium">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
