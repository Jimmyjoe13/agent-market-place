/**
 * Usage Dashboard Component
 * ==========================
 * 
 * Affiche la consommation de l'utilisateur en temps réel :
 * - Requêtes utilisées / limite
 * - Documents / limite
 * - Clés API / limite
 * - Agents / limite
 * 
 * Auto-refresh toutes les 30 secondes.
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
  RefreshCw
} from "lucide-react";
import { 
  useUserUsage, 
  calculateUsagePercentages, 
  getProgressColor,
  type UserUsage 
} from "@/hooks/useUserUsage";
import { cn } from "@/lib/utils";

// ===== Sub-components =====

interface UsageCardProps {
  title: string;
  icon: React.ReactNode;
  used: number;
  limit: number;
  percent: number;
  unit?: string;
}

function UsageCard({ title, icon, used, limit, percent, unit = "" }: UsageCardProps) {
  const isUnlimited = limit === -1;
  const progressColor = getProgressColor(percent);
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-300">
          {icon}
          {title}
        </div>
        <span className="text-sm text-zinc-400">
          {used.toLocaleString()}{unit}
          {" / "}
          {isUnlimited ? "∞" : limit.toLocaleString()}{unit}
        </span>
      </div>
      {/* Progress bar personnalisée */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-zinc-800">
        <div 
          className={cn("h-full transition-all duration-300", progressColor)}
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
    free: "bg-zinc-700 text-zinc-300",
    pro: "bg-indigo-600 text-white",
    enterprise: "bg-purple-600 text-white",
  };
  
  return (
    <div className="flex items-center gap-2">
      <Badge className={cn("uppercase", planColors[plan] || planColors.free)}>
        {plan}
      </Badge>
      {isActive ? (
        <span className="flex items-center gap-1 text-xs text-green-400">
          <CheckCircle className="h-3 w-3" />
          Actif
        </span>
      ) : (
        <span className="text-xs text-zinc-500">{status}</span>
      )}
    </div>
  );
}

// ===== Loading Skeleton =====

function UsageDashboardSkeleton() {
  return (
    <Card className="border-zinc-800 bg-zinc-900/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-40 bg-zinc-800" />
          <Skeleton className="h-5 w-20 bg-zinc-800" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-24 bg-zinc-800" />
              <Skeleton className="h-4 w-16 bg-zinc-800" />
            </div>
            <Skeleton className="h-2 w-full bg-zinc-800" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ===== Main Component =====

interface UsageDashboardProps {
  className?: string;
  showTitle?: boolean;
  compact?: boolean;
  refetchInterval?: number;
}

export function UsageDashboard({ 
  className, 
  showTitle = true,
  compact = false,
  refetchInterval = 30000, 
}: UsageDashboardProps) {
  const { data: usage, isLoading, isError, refetch, isFetching } = useUserUsage({
    refetchInterval,
  });

  if (isLoading) {
    return <UsageDashboardSkeleton />;
  }

  if (isError || !usage) {
    return (
      <Card className={cn("border-zinc-800 bg-zinc-900/50", className)}>
        <CardContent className="py-8 text-center text-zinc-500">
          <AlertTriangle className="mx-auto h-8 w-8 mb-2 text-amber-500" />
          <p>Impossible de charger l{"'"}usage</p>
          <button 
            onClick={() => refetch()}
            className="mt-2 text-sm text-indigo-400 hover:text-indigo-300"
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
    <Card className={cn("border-zinc-800 bg-zinc-900/50", className)}>
      {showTitle && (
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="h-5 w-5 text-indigo-400" />
                Consommation
                {isFetching && (
                  <RefreshCw className="h-3 w-3 animate-spin text-zinc-500" />
                )}
              </CardTitle>
              {!compact && (
                <CardDescription className="text-zinc-500">
                  Période en cours
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
          icon={<Zap className="h-4 w-4 text-indigo-400" />}
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
            icon={<Bot className="h-4 w-4 text-green-400" />}
            used={usage.agents_count || 0}
            limit={usage.agents_limit}
            percent={percentages.agents}
          />
        )}

        {/* Tokens utilisés (si disponible) */}
        {usage.tokens_used !== undefined && usage.tokens_used > 0 && (
          <div className="pt-2 border-t border-zinc-800">
            <div className="flex items-center justify-between text-sm">
              <span className="text-zinc-400">Tokens consommés</span>
              <span className="font-mono text-zinc-300">
                {usage.tokens_used.toLocaleString()}
              </span>
            </div>
          </div>
        )}

        {/* Warning si proche des limites */}
        {hasWarning && !compact && (
          <div className="pt-3 border-t border-zinc-800">
            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 rounded-lg px-3 py-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>
                Vous approchez de vos limites. Pensez à upgrader votre plan.
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default UsageDashboard;
