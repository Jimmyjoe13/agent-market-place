/**
 * Register Page
 * ==============
 *
 * Page d'inscription avec authentification OAuth et Email.
 * Design moderne et premium avec mise en avant des avantages.
 */

import { Suspense } from "react";
import { redirect } from "next/navigation";
import Link from "next/link";
import { createServerSupabaseClient } from "@/lib/supabase-server";
import { RegisterForm } from "@/components/auth/register-form";

// Force dynamic rendering - Supabase client needs runtime env vars
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Inscription | RAG Agent Platform",
  description: "Créez votre compte développeur gratuit et commencez à utiliser l'API",
};

export default async function RegisterPage() {
  // Rediriger si déjà connecté
  const supabase = await createServerSupabaseClient();
  const { data: { user } } = await supabase.auth.getUser();
  
  if (user) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000" />
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000" />
      </div>

      {/* Content */}
      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-cyan-500 mb-4 hover:scale-105 transition-transform">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
          </Link>
          <h1 className="text-3xl font-bold text-white mb-2">
            Créez votre compte
          </h1>
          <p className="text-slate-400">
            Rejoignez des milliers de développeurs qui utilisent RAG Agent
          </p>
        </div>

        {/* Register Card */}
        <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white text-center mb-6">
            Inscription gratuite
          </h2>
          
          <Suspense fallback={<div className="h-12 bg-white/5 rounded-lg animate-pulse" />}>
            <RegisterForm />
          </Suspense>

          <div className="mt-6 text-center">
            <p className="text-sm text-slate-400">
              En vous inscrivant, vous acceptez nos{" "}
              <a href="/terms" className="text-purple-400 hover:text-purple-300 transition-colors">
                Conditions d&apos;utilisation
              </a>{" "}
              et notre{" "}
              <a href="/privacy" className="text-purple-400 hover:text-purple-300 transition-colors">
                Politique de confidentialité
              </a>
            </p>
          </div>
        </div>

        {/* Testimonial / Social Proof */}
        <div className="mt-8 text-center">
          <div className="flex justify-center items-center gap-2 mb-2">
            <div className="flex -space-x-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-cyan-400 border-2 border-slate-900"
                />
              ))}
            </div>
            <span className="text-slate-400 text-sm ml-2">+500 développeurs</span>
          </div>
          <p className="text-xs text-slate-500">
            Rejoignez une communauté en pleine croissance
          </p>
        </div>
      </div>
    </div>
  );
}
