/**
 * Dashboard - Analytics et statistiques
 * ======================================
 * 
 * Affiche les métriques clés avec :
 * - Sélecteur de période (7j, 30j, 90j)
 * - Indicateurs de tendance sur les StatCards
 * - Distribution des scores
 * - Consommation temps réel
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { 
  BarChart3, 
  MessageSquare, 
  ThumbsUp, 
  BookOpen, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle, 
  RefreshCw,
  Minus
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { DashboardSkeleton, UsageDashboard } from "@/components/dashboard";
import { PeriodSelector, type Period } from "@/components/dashboard/PeriodSelector";
import type { AnalyticsResponse } from "@/types/api";

// ===== StatCard with Enhanced Trend =====

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  colorClass: string;
  trend?: number;
  loading?: boolean;
}

function StatCard({ title, value, icon: Icon, colorClass, trend, loading }: StatCardProps) {
  const getTrendIcon = () => {
    if (trend === undefined || trend === 0) return <Minus className="h-3 w-3" />;
    return trend > 0 
      ? <TrendingUp className="h-3 w-3" /> 
      : <TrendingDown className="h-3 w-3" />;
  };

  const getTrendColor = () => {
    if (trend === undefined || trend === 0) return "text-muted-foreground";
    return trend > 0 ? "text-success" : "text-destructive";
  };

  return (
    <Card className="border-border bg-card card-hover relative overflow-hidden">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-card/80 flex items-center justify-center z-10">
          <RefreshCw className="h-4 w-4 animate-spin text-primary" />
        </div>
      )}
      
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`h-8 w-8 rounded-lg ${colorClass} flex items-center justify-center`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-bold text-foreground transition-all duration-300">
            {value}
          </span>
          {trend !== undefined && (
            <span 
              className={`text-xs font-medium flex items-center gap-0.5 ${getTrendColor()} transition-colors duration-200`}
            >
              {getTrendIcon()}
              {trend !== 0 && `${Math.abs(trend)}%`}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ===== Error State =====

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <div className="h-16 w-16 rounded-2xl bg-destructive/10 flex items-center justify-center mb-4">
        <AlertTriangle className="h-8 w-8 text-destructive" />
      </div>
      <h2 className="mb-2 text-xl font-semibold text-foreground">Analytics indisponibles</h2>
      <p className="text-muted-foreground mb-6 max-w-md">{message}</p>
      <Button onClick={onRetry} variant="outline" className="gap-2">
        <RefreshCw className="h-4 w-4" />
        Réessayer
      </Button>
    </div>
  );
}

// ===== Helper: Calculate Trend =====

function calculateTrend(current: number, previous: number): number {
  if (previous === 0) {
    return current > 0 ? 100 : 0;
  }
  return Math.round(((current - previous) / previous) * 100);
}

// ===== Period Label =====

function getPeriodLabel(period: Period): string {
  switch (period) {
    case 7: return "7 derniers jours";
    case 30: return "30 derniers jours";
    case 90: return "90 derniers jours";
  }
}

// ===== Main Component =====

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>(30);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [previousAnalytics, setPreviousAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async (selectedPeriod: Period, isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);
    
    try {
      // Fetch current period analytics
      const data = await api.getAnalytics(selectedPeriod);
      setAnalytics(data);
      
      // Fetch previous period for trend comparison
      // For 7 days, compare with previous 7 days
      // For 30 days, compare with previous 30 days, etc.
      try {
        const previousData = await api.getAnalytics(selectedPeriod * 2);
        // Calculate previous period by subtracting current from double period
        setPreviousAnalytics({
          total_conversations: Math.max(0, (previousData.total_conversations || 0) - (data.total_conversations || 0)),
          total_feedbacks: Math.max(0, (previousData.total_feedbacks || 0) - (data.total_feedbacks || 0)),
          average_score: previousData.average_score, // Keep average as is for comparison
          pending_training: previousData.pending_training || 0,
          score_distribution: previousData.score_distribution || {},
        });
      } catch {
        // If we can't get previous data, just don't show trends
        setPreviousAnalytics(null);
      }
    } catch (err) {
      setError("Impossible de charger les analytics. Vérifiez votre connexion.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchAnalytics(period);
  }, []);

  // Handle period change
  const handlePeriodChange = useCallback((newPeriod: Period) => {
    setPeriod(newPeriod);
    fetchAnalytics(newPeriod, true);
  }, [fetchAnalytics]);

  // Manual refresh
  const handleRefresh = () => {
    fetchAnalytics(period, true);
  };

  // Calculate trends
  const conversationsTrend = previousAnalytics
    ? calculateTrend(analytics?.total_conversations || 0, previousAnalytics.total_conversations || 0)
    : undefined;
  
  const feedbacksTrend = previousAnalytics
    ? calculateTrend(analytics?.total_feedbacks || 0, previousAnalytics.total_feedbacks || 0)
    : undefined;

  // État de chargement initial
  if (loading) {
    return <DashboardSkeleton />;
  }

  // État d'erreur
  if (error) {
    return <ErrorState message={error} onRetry={handleRefresh} />;
  }

  return (
    <div className="h-full overflow-y-auto p-8 custom-scrollbar">
      <div className="mx-auto max-w-6xl">
        {/* Header with Period Selector */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground">
              Statistiques des {getPeriodLabel(period).toLowerCase()}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <PeriodSelector value={period} onChange={handlePeriodChange} />
            <Button 
              variant="outline" 
              size="icon" 
              onClick={handleRefresh}
              disabled={refreshing}
              className="shrink-0"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Stats Grid with Trends */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Conversations"
            value={analytics?.total_conversations || 0}
            icon={MessageSquare}
            colorClass="bg-primary/10 text-primary"
            trend={conversationsTrend}
            loading={refreshing}
          />
          <StatCard
            title="Feedbacks"
            value={analytics?.total_feedbacks || 0}
            icon={ThumbsUp}
            colorClass="bg-success/10 text-success"
            trend={feedbacksTrend}
            loading={refreshing}
          />
          <StatCard
            title="Score Moyen"
            value={analytics?.average_score?.toFixed(1) || "N/A"}
            icon={BarChart3}
            colorClass="bg-accent text-accent-foreground"
            loading={refreshing}
          />
          <StatCard
            title="En attente"
            value={analytics?.pending_training || 0}
            icon={BookOpen}
            colorClass="bg-warning/10 text-warning"
            loading={refreshing}
          />
        </div>

        {/* Usage & Consumption Dashboard */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <UsageDashboard />
          
          {/* Score Distribution Chart */}
          {analytics?.score_distribution && Object.keys(analytics.score_distribution).length > 0 ? (
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">Distribution des scores</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex h-32 items-end gap-2">
                  {[1, 2, 3, 4, 5].map((score) => {
                    const count = analytics.score_distribution[score.toString()] || 0;
                    const maxCount = Math.max(
                      ...Object.values(analytics.score_distribution)
                    );
                    const height = maxCount > 0 ? (count / maxCount) * 100 : 0;

                    return (
                      <div key={score} className="flex flex-1 flex-col items-center gap-2 group">
                        <div
                          className="w-full rounded-t bg-gradient-brand transition-all duration-300 group-hover:opacity-80"
                          style={{ height: `${height}%`, minHeight: count > 0 ? "8px" : "0" }}
                        />
                        <span className="text-sm text-muted-foreground">{score}★</span>
                        <span className="text-xs text-muted-foreground/70">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border bg-card">
              <CardContent className="py-12 text-center">
                <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground/30" />
                <p className="text-muted-foreground">Aucune donnée de score disponible</p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Les scores apparaîtront lorsque vous aurez des feedbacks
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
