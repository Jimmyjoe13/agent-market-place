/**
 * Composants d'états réutilisables (Empty, Error, Loading)
 * Ces composants permettent d'afficher des états visuels cohérents dans toute l'application
 */

"use client";

import { AlertCircle, FileQuestion, Loader2, RefreshCw, WifiOff } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

// ===== Interfaces =====

interface StateProps {
  className?: string;
}

interface EmptyStateProps extends StateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ErrorStateProps extends StateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  variant?: "default" | "inline" | "card";
}

interface LoadingStateProps extends StateProps {
  text?: string;
  size?: "sm" | "md" | "lg";
}

// ===== Empty State =====

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-900">
        {icon || <FileQuestion className="h-8 w-8 text-zinc-500" />}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-zinc-200">{title}</h3>
      {description && (
        <p className="mb-4 max-w-md text-sm text-zinc-400">{description}</p>
      )}
      {action && (
        <Button
          onClick={action.onClick}
          variant="outline"
          className="mt-2 border-zinc-700 hover:bg-zinc-800"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

// ===== Error State =====

export function ErrorState({
  title = "Une erreur est survenue",
  description = "Impossible de charger les données. Veuillez réessayer.",
  onRetry,
  retryLabel = "Réessayer",
  variant = "default",
  className,
}: ErrorStateProps) {
  if (variant === "inline") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-lg bg-red-500/10 p-4 text-red-400",
          className
        )}
      >
        <AlertCircle className="h-5 w-5 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium">{title}</p>
          {description && (
            <p className="text-xs text-red-400/80">{description}</p>
          )}
        </div>
        {onRetry && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onRetry}
            className="shrink-0 text-red-400 hover:bg-red-500/20 hover:text-red-300"
          >
            <RefreshCw className="mr-1 h-4 w-4" />
            {retryLabel}
          </Button>
        )}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn(
          "rounded-lg border border-red-500/20 bg-red-500/5 p-6",
          className
        )}
      >
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
            <AlertCircle className="h-5 w-5 text-red-400" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-red-400">{title}</h4>
            {description && (
              <p className="mt-1 text-sm text-red-400/70">{description}</p>
            )}
            {onRetry && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRetry}
                className="mt-4 border-red-500/30 text-red-400 hover:bg-red-500/10"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                {retryLabel}
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Default variant (centered)
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10">
        <WifiOff className="h-8 w-8 text-red-400" />
      </div>
      <h3 className="mb-2 text-lg font-semibold text-red-400">{title}</h3>
      {description && (
        <p className="mb-4 max-w-md text-sm text-red-400/70">{description}</p>
      )}
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          className="border-red-500/30 text-red-400 hover:bg-red-500/10"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          {retryLabel}
        </Button>
      )}
    </div>
  );
}

// ===== Loading State =====

export function LoadingState({
  text = "Chargement...",
  size = "md",
  className,
}: LoadingStateProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  const textSizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 p-8",
        className
      )}
    >
      <Loader2
        className={cn("animate-spin text-indigo-400", sizeClasses[size])}
      />
      {text && (
        <p className={cn("text-zinc-400", textSizeClasses[size])}>{text}</p>
      )}
    </div>
  );
}

// ===== Loading Spinner Inline =====

export function LoadingSpinner({
  size = "md",
  className,
}: {
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };

  return (
    <Loader2
      className={cn("animate-spin text-indigo-400", sizeClasses[size], className)}
    />
  );
}
