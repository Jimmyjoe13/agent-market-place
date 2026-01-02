/**
 * Usage Dashboard Component
 * ==========================
 * 
 * Affiche la consommation de l'utilisateur en TEMPS RÉEL via Supabase Realtime :
 * - Requêtes utilisées / limite
 * - Documents / limite
 * - Clés API / limite
 * - Agents / limite
 * 
 * Features:
 * - Indicateur de connexion temps réel (Live)
 * - Animation des valeurs lors des changements
 * - Fallback polling si Realtime indisponible
 * - Timestamp "Dernière mise à jour"
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Zap, 
  FileText, 
  Key, 
  Bot, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Clock
} from "lucide-react";
import { 
  useRealtimeUsage, 
  calculateUsagePercentages, 
  getProgressColor,
  type UserUsage 
} from "@/hooks/useRealtimeUsage";
import { LiveIndicator } from "./LiveIndicator";
import { AnimatedCounter } from "./AnimatedCounter";
import { cn } from "@/lib/utils";

// ===== Sub-components =====

interface UsageCardProps {
  title: string;
  icon: React.ReactNode;
  used: number;
  limit: number;
  percent: number;
  unit?: string;
  animate?: boolean;
}

function UsageCard({ title, icon, used, limit, percent, unit = "", animate = true }: UsageCardProps) {
  const isUnlimited = limit === -1;
  const progressColor = getProgressColor(percent);
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          {icon}
          {title}
        </div>
        <span className="text-sm text-muted-foreground">
          {animate ? (
            <AnimatedCounter 
              value={used} 
              className="font-medium text-foreground"
            />
          ) : (
            <span className="font-medium text-foreground">{used.toLocaleString()}</span>
          )}
          {unit}
          {" / "}
          {isUnlimited ? "∞" : limit.toLocaleString()}{unit}
        </span>
      </div>
      {/* Progress bar personnalisée */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
        <div 
          className={cn("h-full transition-all duration-500 ease-out", progressColor)}
          style={{ width: isUnlimited ? "0%" : `${percent}%` }}
        />
      </div>
      {!isUnlimited && percent >= 90 && (
        <div className="flex items-center gap-1 text-xs text-red-400">
          <AlertTriangle className="h-3 w-3" />
          Limite bientôt atteinte
        </div>
      )}
    </div>
  );
}

interface PlanBadgeProps {
  plan: string;
  status: string;
}

function PlanBadge({ plan, status }: PlanBadgeProps) {
  const isActive = status === "active";
  
  const planColors: Record<string, string> = {
    free: "bg-muted text-muted-foreground",
    pro: "bg-primary text-primary-foreground",
    enterprise: "bg-purple-600 text-white",
  };
  
  return (
    <div className="flex items-center gap-2">
      <Badge className={cn("uppercase", planColors[plan] || planColors.free)}>
        {plan}
      </Badge>
      {isActive ? (
        <span className="flex items-center gap-1 text-xs text-success">
          <CheckCircle className="h-3 w-3" />
          Actif
        </span>
      ) : (
        <span className="text-xs text-muted-foreground">{status}</span>
      )}
    </div>
  );
}

// ===== Loading Skeleton =====

function UsageDashboardSkeleton() {
  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-5 w-20" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-2 w-full" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ===== Helper: Format relative time =====

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffSeconds < 5) return "À l'instant";
  if (diffSeconds < 60) return `Il y a ${diffSeconds}s`;
  if (diffSeconds < 3600) return `Il y a ${Math.floor(diffSeconds / 60)}min`;
  return `Il y a ${Math.floor(diffSeconds / 3600)}h`;
}

// ===== Main Component =====

interface UsageDashboardProps {
  className?: string;
  showTitle?: boolean;
  compact?: boolean;
  /** @deprecated Use realtime by default now */
  refetchInterval?: number;
  /** Show live indicator */
  showLiveIndicator?: boolean;
  /** Show last updated timestamp */
  showLastUpdated?: boolean;
}

export function UsageDashboard({ 
  className, 
  showTitle = true,
  compact = false,
  showLiveIndicator = true,
  showLastUpdated = true,
}: UsageDashboardProps) {
  const { 
    usage, 
    isLoading, 
    isError, 
    refetch, 
    connectionStatus,
    lastUpdated 
  } = useRealtimeUsage();

  if (isLoading) {
    return <UsageDashboardSkeleton />;
  }

  if (isError || !usage) {
    return (
      <Card className={cn("border-border bg-card", className)}>
        <CardContent className="py-8 text-center text-muted-foreground">
          <AlertTriangle className="mx-auto h-8 w-8 mb-2 text-warning" />
          <p>Impossible de charger l{"'"}usage</p>
          <button 
            onClick={() => refetch()}
            className="mt-2 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Réessayer
          </button>
        </CardContent>
      </Card>
    );
  }

  const percentages = calculateUsagePercentages(usage);
  const hasWarning = percentages.requests >= 75 || percentages.documents >= 75;

  return (
    <Card className={cn("border-border bg-card", className)}>
      {showTitle && (
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="h-5 w-5 text-primary" />
                Consommation
                {showLiveIndicator && (
                  <LiveIndicator status={connectionStatus} showLabel={false} />
                )}
              </CardTitle>
              {!compact && (
                <CardDescription className="flex items-center gap-2 mt-1">
                  <span>Période en cours</span>
                  {showLastUpdated && lastUpdated && (
                    <>
                      <span className="text-muted-foreground/50">•</span>
                      <span className="flex items-center gap-1 text-xs">
                        <Clock className="h-3 w-3" />
                        {formatRelativeTime(lastUpdated)}
                      </span>
                    </>
                  )}
                </CardDescription>
              )}
            </div>
            <PlanBadge plan={usage.plan} status={usage.subscription_status} />
          </div>
        </CardHeader>
      )}
      
      <CardContent className={cn("space-y-4", compact && "pt-4")}>
        {/* Requêtes */}
        <UsageCard
          title="Requêtes API"
          icon={<Zap className="h-4 w-4 text-primary" />}
          used={usage.requests_count}
          limit={usage.requests_limit}
          percent={percentages.requests}
        />

        {/* Documents */}
        <UsageCard
          title="Documents"
          icon={<FileText className="h-4 w-4 text-purple-400" />}
          used={usage.documents_count}
          limit={usage.documents_limit}
          percent={percentages.documents}
        />

        {/* Clés API */}
        <UsageCard
          title="Clés API"
          icon={<Key className="h-4 w-4 text-cyan-400" />}
          used={usage.api_keys_count}
          limit={usage.api_keys_limit}
          percent={percentages.apiKeys}
        />

        {/* Agents (si disponible) */}
        {usage.agents_limit !== undefined && (
          <UsageCard
            title="Agents"
            icon={<Bot className="h-4 w-4 text-success" />}
            used={usage.agents_count || 0}
            limit={usage.agents_limit}
            percent={percentages.agents}
          />
        )}

        {/* Tokens utilisés (si disponible) */}
        {usage.tokens_used !== undefined && usage.tokens_used > 0 && (
          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Tokens consommés</span>
              <AnimatedCounter 
                value={usage.tokens_used} 
                className="font-mono text-foreground"
              />
            </div>
          </div>
        )}

        {/* Warning si proche des limites */}
        {hasWarning && !compact && (
          <div className="pt-3 border-t border-border">
            <div className="flex items-center gap-2 text-xs text-warning bg-warning/10 rounded-lg px-3 py-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>
                Vous approchez de vos limites. Pensez à upgrader votre plan.
              </span>
            </div>
          </div>
        )}

        {/* Connection status footer for compact mode */}
        {compact && showLiveIndicator && (
          <div className="pt-2 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <LiveIndicator status={connectionStatus} />
            {lastUpdated && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatRelativeTime(lastUpdated)}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default UsageDashboard;
