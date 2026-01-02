/**
 * Usage Dashboard Component
 * ==========================
 * 
 * Affiche la consommation de l'utilisateur en TEMPS RÉEL avec :
 * - Tracking des limites (requêtes, docs, clés, agents)
 * - Prévisions de consommation basées sur le rythme actuel
 * - Alertes d'usage (bannières contextuelles)
 * - Export des données en CSV
 * - Esthétique Premium (glassmorphism, animations)
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { 
  Zap, 
  FileText, 
  Key, 
  Bot, 
  TrendingUp, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Download,
  Calendar,
  Sparkles,
  Info,
  RefreshCw
} from "lucide-react";
import { 
  useRealtimeUsage, 
  calculateUsagePercentages, 
  calculateUsageForecast,
  getProgressColor,
  type UserUsage 
} from "@/hooks/useRealtimeUsage";
import { LiveIndicator } from "./LiveIndicator";
import { AnimatedCounter } from "./AnimatedCounter";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

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
  
  // Forecast for this specific metric
  const forecast = calculateUsageForecast(used, limit);
  
  return (
    <div className="space-y-2 group">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">
          <div className="p-1 rounded bg-muted group-hover:bg-primary/10 transition-colors">
            {icon}
          </div>
          {title}
        </div>
        <div className="text-right">
          <div className="text-sm">
            {animate ? (
              <AnimatedCounter 
                value={used} 
                className="font-bold text-foreground"
              />
            ) : (
              <span className="font-bold text-foreground">{used.toLocaleString()}</span>
            )}
            <span className="text-muted-foreground/60 ml-1">
              / {isUnlimited ? "∞" : limit.toLocaleString()}{unit}
            </span>
          </div>
        </div>
      </div>
      
      {/* Progress bar glassmorphism style */}
      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted/40 backdrop-blur-sm border border-border/50">
        <div 
          className={cn("h-full transition-all duration-700 ease-out shadow-sm", progressColor)}
          style={{ width: isUnlimited ? "0%" : `${percent}%` }}
        />
        {/* Forecast marker (subtle) */}
        {!isUnlimited && forecast.forecastValue > used && (
          <div 
            className="absolute top-0 h-full border-r border-dashed border-foreground/30 z-10 opacity-40"
            style={{ 
              left: `${Math.min(100, (forecast.forecastValue / limit) * 100)}%`,
              display: (forecast.forecastValue / limit) * 100 > percent ? 'block' : 'none'
            }}
          />
        )}
      </div>

      {/* Forecast & Alerts */}
      <div className="flex items-center justify-between text-[10px] sm:text-xs">
        {!isUnlimited && (
          <div className="flex items-center gap-1.5 text-muted-foreground/70">
            {forecast.willExceed ? (
              <span className="flex items-center gap-1 text-red-400 font-medium">
                <AlertTriangle className="h-3 w-3" />
                Dépassement prévu ({forecast.forecastValue})
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                Est. fin de mois: {forecast.forecastValue}
              </span>
            )}
          </div>
        )}
        
        {!isUnlimited && percent >= 80 && (
          <Badge variant="outline" className={cn(
            "h-5 text-[9px] px-1.5 border-none",
            percent >= 95 ? "bg-red-500/10 text-red-500" : "bg-amber-500/10 text-amber-500"
          )}>
            {percent >= 95 ? "Critique" : "Quasi plein"}
          </Badge>
        )}
      </div>
    </div>
  );
}

// ===== Export Function =====

const exportUsageToCSV = (usage: UserUsage) => {
  const currentMonth = new Date().toLocaleString('default', { month: 'long', year: 'numeric' });
  const rows = [
    ["Metric", "Used", "Limit", "Percentage"],
    ["Requêtes API", usage.requests_count, usage.requests_limit === -1 ? "Unlimited" : usage.requests_limit, `${Math.round((usage.requests_count / usage.requests_limit) * 100)}%`],
    ["Documents", usage.documents_count, usage.documents_limit === -1 ? "Unlimited" : usage.documents_limit, `${Math.round((usage.documents_count / usage.documents_limit) * 100)}%`],
    ["Clés API", usage.api_keys_count, usage.api_keys_limit === -1 ? "Unlimited" : usage.api_keys_limit, `${Math.round((usage.api_keys_count / usage.api_keys_limit) * 100)}%`],
    ["Agents", usage.agents_count || 0, usage.agents_limit === -1 ? "Unlimited" : usage.agents_limit, `${Math.round(((usage.agents_count || 0) / (usage.agents_limit || 1)) * 100)}%`],
    ["Tokens", usage.tokens_used || 0, "N/A", "N/A"]
  ];

  const csvContent = "data:text/csv;charset=utf-8," 
    + `RAG Agent - Usage Report - ${currentMonth}\n`
    + rows.map(e => e.join(",")).join("\n");

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `rag_usage_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// ===== Main Component =====

export function UsageDashboard() {
  const { 
    usage, 
    isLoading, 
    isError, 
    connectionStatus,
    lastUpdated 
  } = useRealtimeUsage();

  const [isExporting, setIsExporting] = useState(false);

  if (isLoading) return <UsageDashboardSkeleton />;
  if (isError || !usage) return <UsageErrorState />;

  const percentages = calculateUsagePercentages(usage);
  const quotaForecast = calculateUsageForecast(usage.requests_count, usage.requests_limit);
  
  const handleExport = () => {
    setIsExporting(true);
    exportUsageToCSV(usage);
    setTimeout(() => setIsExporting(false), 1000);
  };

  return (
    <Card className="border-border bg-card/50 backdrop-blur-md relative overflow-hidden group">
      {/* Decorative gradient background effect */}
      <div className="absolute top-0 right-0 -m-8 h-40 w-40 rounded-full bg-primary/5 blur-3xl group-hover:bg-primary/10 transition-all duration-1000" />
      
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-lg font-bold">
              <Zap className="h-5 w-5 text-primary fill-primary/20" />
              Consommation
              <LiveIndicator status={connectionStatus} showLabel={false} />
            </CardTitle>
            <CardDescription className="flex items-center gap-1.5">
              <Calendar className="h-3 w-3" />
              {usage.period || "Période en cours"}
              <span className="text-muted-foreground/30">•</span>
              <span className="text-xs">{quotaForecast.daysRemaining} jours restants</span>
            </CardDescription>
          </div>
          
          <div className="flex flex-col items-end gap-2">
            <Badge className={cn(
              "uppercase font-bold tracking-wider px-2 py-0.5 border-none shadow-sm",
              usage.plan === 'enterprise' ? "bg-purple-600" : 
              usage.plan === 'pro' ? "bg-primary" : "bg-muted text-muted-foreground"
            )}>
              {usage.plan}
            </Badge>
            {lastUpdated && (
              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                <Clock className="h-2.5 w-2.5" />
                Màj {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Info Banner when forecasting exceeding */}
        {quotaForecast.willExceed && (
          <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20 flex gap-3 animate-in fade-in slide-in-from-top-2 duration-500">
            <Sparkles className="h-5 w-5 text-orange-400 shrink-0" />
            <div className="text-xs space-y-1">
              <p className="font-bold text-orange-400">Optimisation prédictive</p>
              <p className="text-muted-foreground leading-relaxed">
                Votre rythme actuel suggère que vous atteindrez votre limite de requêtes 
                dans environ <span className="text-orange-300 font-medium">{Math.floor(usage.requests_limit / (usage.requests_count / Math.max(1, new Date().getDate())))} jours</span>.
              </p>
            </div>
          </div>
        )}

        <div className="space-y-5">
          <UsageCard
            title="Requêtes API"
            icon={<Zap className="h-3.5 w-3.5 text-primary" />}
            used={usage.requests_count}
            limit={usage.requests_limit}
            percent={percentages.requests}
          />

          <UsageCard
            title="Documents RAG"
            icon={<FileText className="h-3.5 w-3.5 text-purple-400" />}
            used={usage.documents_count}
            limit={usage.documents_limit}
            percent={percentages.documents}
          />

          <div className="grid grid-cols-2 gap-4">
            <UsageCard
              title="Clés API"
              icon={<Key className="h-3.5 w-3.5 text-cyan-400" />}
              used={usage.api_keys_count}
              limit={usage.api_keys_limit}
              percent={percentages.apiKeys}
            />
            
            {usage.agents_limit !== undefined && (
              <UsageCard
                title="Agents"
                icon={<Bot className="h-3.5 w-3.5 text-success" />}
                used={usage.agents_count || 0}
                limit={usage.agents_limit}
                percent={percentages.agents}
              />
            )}
          </div>
        </div>

        {/* Tokens Footprint */}
        {usage.tokens_used !== undefined && (
          <div className="pt-4 border-t border-border/50">
            <div className="flex items-center justify-between text-xs px-1">
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Info className="h-3 w-3" />
                <span>Consommation de tokens</span>
              </div>
              <div className="flex items-center gap-2">
                <AnimatedCounter 
                  value={usage.tokens_used} 
                  className="font-mono text-foreground font-bold"
                />
                <span className="text-[10px] text-muted-foreground uppercase opacity-70">tkns</span>
              </div>
            </div>
          </div>
        )}

        {/* Actions Footer */}
        <div className="pt-2 flex items-center justify-between">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-8 text-[11px] gap-1.5 text-muted-foreground hover:text-foreground"
                  onClick={handleExport}
                  disabled={isExporting}
                >
                  <Download className={cn("h-3.5 w-3.5", isExporting && "animate-bounce")} />
                  Exporter (.csv)
                </Button>
              </TooltipTrigger>
              <TooltipContent>Exporter l{"'"}usage mensuel</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 text-[11px] font-bold border-primary/20 hover:border-primary/50 group"
          >
            Upgrade Plan
            <TrendingUp className="ml-1.5 h-3 w-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ===== Internal Components =====

function UsageDashboardSkeleton() {
  return (
    <Card className="border-border bg-card/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-5 w-20" />
        </div>
      </CardHeader>
      <CardContent className="space-y-6 pt-2">
        <Skeleton className="h-12 w-full rounded-lg" />
        {[1, 2, 3].map((i) => (
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

function UsageErrorState() {
  return (
    <Card className="border-border bg-card/50 border-dashed">
      <CardContent className="py-12 text-center text-muted-foreground space-y-4">
        <div className="bg-destructive/10 h-12 w-12 rounded-full flex items-center justify-center mx-auto mb-2">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <div className="space-y-1">
          <p className="font-bold text-foreground">Analytics temporairement indisponibles</p>
          <p className="text-xs">Nous n{"'"}avons pas pu récupérer vos données en temps réel.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="gap-2">
          <RefreshCw className="h-3 w-3" />
          Réactualiser
        </Button>
      </CardContent>
    </Card>
  );
}

export default UsageDashboard;
