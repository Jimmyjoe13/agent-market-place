/**
 * LiveIndicator Component
 * =======================
 * 
 * Indicateur visuel du statut de connexion temps réel.
 * 
 * - Vert pulsant = Connecté (Live)
 * - Jaune = Reconnexion en cours
 * - Gris = Déconnecté (mode polling)
 */

"use client";

import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/hooks/useRealtimeUsage";

interface LiveIndicatorProps {
  status: ConnectionStatus;
  showLabel?: boolean;
  className?: string;
}

const statusConfig: Record<ConnectionStatus, {
  dotClass: string;
  label: string;
  animate: boolean;
}> = {
  connected: {
    dotClass: "bg-green-500",
    label: "Live",
    animate: true,
  },
  connecting: {
    dotClass: "bg-amber-500",
    label: "Connexion...",
    animate: true,
  },
  disconnected: {
    dotClass: "bg-zinc-500",
    label: "Hors ligne",
    animate: false,
  },
};

export function LiveIndicator({ 
  status, 
  showLabel = true,
  className 
}: LiveIndicatorProps) {
  const config = statusConfig[status];
  
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {/* Dot avec animation pulse */}
      <span className="relative flex h-2 w-2">
        {config.animate && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full rounded-full opacity-75",
              config.dotClass,
              "animate-ping"
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            config.dotClass
          )}
        />
      </span>
      
      {/* Label optionnel */}
      {showLabel && (
        <span 
          className={cn(
            "text-xs font-medium",
            status === "connected" && "text-green-500",
            status === "connecting" && "text-amber-500",
            status === "disconnected" && "text-zinc-500"
          )}
        >
          {config.label}
        </span>
      )}
    </div>
  );
}

export default LiveIndicator;
