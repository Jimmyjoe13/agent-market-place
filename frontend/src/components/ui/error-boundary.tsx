/**
 * Error Boundary pour capturer les erreurs React
 * Affiche un fallback UI en cas d'erreur
 */

"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react";
import { Button } from "./button";

// ===== Types =====

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetKeys?: unknown[];
  level?: "page" | "section" | "component";
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// ===== Error Boundary Class =====

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    
    // Log l'erreur
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    
    // Callback optionnel
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    // Reset si les resetKeys changent
    if (this.state.hasError && this.props.resetKeys) {
      const prevResetKeys = prevProps.resetKeys || [];
      const currentResetKeys = this.props.resetKeys;
      
      const hasChanged = currentResetKeys.some(
        (key, index) => key !== prevResetKeys[index]
      );
      
      if (hasChanged) {
        this.reset();
      }
    }
  }

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          resetError={this.reset}
          level={this.props.level || "section"}
        />
      );
    }

    return this.props.children;
  }
}

// ===== Error Fallback UI =====

interface ErrorFallbackProps {
  error: Error | null;
  resetError: () => void;
  level: "page" | "section" | "component";
}

function ErrorFallback({ error, resetError, level }: ErrorFallbackProps) {
  const isProduction = process.env.NODE_ENV === "production";

  if (level === "component") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm text-red-400">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>Erreur de composant</span>
        <Button
          size="sm"
          variant="ghost"
          onClick={resetError}
          className="ml-auto h-6 px-2 text-red-400 hover:text-red-300"
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  if (level === "section") {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 p-8">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
          <AlertTriangle className="h-6 w-6 text-red-400" />
        </div>
        <h3 className="mb-2 font-semibold text-red-400">
          Une erreur est survenue
        </h3>
        <p className="mb-4 max-w-md text-center text-sm text-red-400/70">
          Cette section a rencontré un problème.
          Essayez de la recharger.
        </p>
        {!isProduction && error && (
          <details className="mb-4 w-full max-w-lg">
            <summary className="cursor-pointer text-xs text-zinc-500">
              Détails techniques
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-zinc-900 p-3 text-xs text-red-400">
              {error.message}
              {"\n\n"}
              {error.stack}
            </pre>
          </details>
        )}
        <Button
          onClick={resetError}
          variant="outline"
          className="gap-2 border-red-500/30 text-red-400 hover:bg-red-500/10"
        >
          <RefreshCw className="h-4 w-4" />
          Réessayer
        </Button>
      </div>
    );
  }

  // Level: page
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 p-8">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500/20 to-orange-500/20">
        <Bug className="h-10 w-10 text-red-400" />
      </div>
      <h1 className="mb-2 text-2xl font-bold text-white">
        Oups ! Quelque chose s&apos;est mal passé
      </h1>
      <p className="mb-6 max-w-md text-center text-zinc-400">
        L&apos;application a rencontré une erreur inattendue.
        Veuillez réessayer ou retourner à l&apos;accueil.
      </p>
      {!isProduction && error && (
        <details className="mb-6 w-full max-w-xl">
          <summary className="cursor-pointer text-sm text-zinc-500">
            Afficher les détails de l&apos;erreur
          </summary>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-zinc-900 p-4 text-xs text-red-400">
            {error.name}: {error.message}
            {"\n\n"}
            {error.stack}
          </pre>
        </details>
      )}
      <div className="flex gap-3">
        <Button
          onClick={resetError}
          variant="outline"
          className="gap-2 border-zinc-700"
        >
          <RefreshCw className="h-4 w-4" />
          Réessayer
        </Button>
        <Button
          onClick={() => window.location.href = "/"}
          className="gap-2 bg-indigo-600 hover:bg-indigo-500"
        >
          <Home className="h-4 w-4" />
          Retour à l&apos;accueil
        </Button>
      </div>
    </div>
  );
}

// ===== Wrapper Components =====

interface SectionErrorBoundaryProps {
  children: ReactNode;
  name?: string;
}

export function SectionErrorBoundary({ children, name }: SectionErrorBoundaryProps) {
  return (
    <ErrorBoundary
      level="section"
      onError={(error) => {
        console.error(`[Section: ${name || "Unknown"}] Error:`, error);
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

export function PageErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary level="page">
      {children}
    </ErrorBoundary>
  );
}

export function ComponentErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary level="component">
      {children}
    </ErrorBoundary>
  );
}

export default ErrorBoundary;
