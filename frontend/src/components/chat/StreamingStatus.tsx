/**
 * StreamingStatus Component
 * ==========================
 * 
 * Affiche l'état de la connexion streaming :
 * - Indicateur de reconnexion
 * - Compteur de retry
 * - Bouton retry manuel
 */

"use client";

import { RefreshCw, WifiOff, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface StreamingStatusProps {
  isReconnecting: boolean;
  retryCount: number;
  maxRetries?: number;
  error: string | null;
  onRetry?: () => void;
  className?: string;
}

export function StreamingStatus({
  isReconnecting,
  retryCount,
  maxRetries = 3,
  error,
  onRetry,
  className,
}: StreamingStatusProps) {
  // Pas d'état particulier à afficher
  if (!isReconnecting && !error) {
    return null;
  }

  // État de reconnexion automatique
  if (isReconnecting) {
    return (
      <div 
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-lg",
          "bg-amber-500/10 border border-amber-500/20",
          "text-amber-400 text-sm",
          className
        )}
      >
        <RefreshCw className="h-4 w-4 animate-spin" />
        <span>
          Reconnexion en cours... ({retryCount}/{maxRetries})
        </span>
      </div>
    );
  }

  // État d'erreur avec option retry
  if (error) {
    return (
      <div 
        className={cn(
          "flex items-center justify-between gap-3 px-3 py-2 rounded-lg",
          "bg-red-500/10 border border-red-500/20",
          "text-red-400 text-sm",
          className
        )}
      >
        <div className="flex items-center gap-2">
          {error.includes("contacter") || error.includes("Network") ? (
            <WifiOff className="h-4 w-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
          )}
          <span>{error}</span>
        </div>
        
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRetry}
            className="text-red-400 hover:text-red-300 hover:bg-red-500/20 h-7 px-2"
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Réessayer
          </Button>
        )}
      </div>
    );
  }

  return null;
}

export default StreamingStatus;
