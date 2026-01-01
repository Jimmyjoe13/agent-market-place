/**
 * Dashboard - Analytics et statistiques
 * ======================================
 * 
 * Affiche les métriques clés et la distribution des scores.
 * Utilise des skeletons pour un chargement fluide.
 */

"use client";

import { useEffect, useState } from "react";
import { BarChart3, MessageSquare, ThumbsUp, BookOpen, TrendingUp, AlertTriangle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { DashboardSkeleton, UsageDashboard } from "@/components/dashboard";
import type { AnalyticsResponse } from "@/types/api";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  colorClass: string;
  trend?: number;
}

function StatCard({ title, value, icon: Icon, colorClass, trend }: StatCardProps) {
  return (
    <Card className="border-border bg-card card-hover">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`h-8 w-8 rounded-lg ${colorClass} flex items-center justify-center`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-2">
          <span className="text-2xl font-bold text-foreground">{value}</span>
          {trend !== undefined && (
            <span className={`text-xs font-medium flex items-center gap-0.5 ${trend >= 0 ? 'text-success' : 'text-destructive'}`}>
              <TrendingUp className={`h-3 w-3 ${trend < 0 ? 'rotate-180' : ''}`} />
              {Math.abs(trend)}%
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

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

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAnalytics(30);
      setAnalytics(data);
    } catch (err) {
      setError("Impossible de charger les analytics. Vérifiez votre clé API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  // État de chargement avec skeleton structuré
  if (loading) {
    return <DashboardSkeleton />;
  }

  // État d'erreur avec bouton retry
  if (error) {
    return <ErrorState message={error} onRetry={fetchAnalytics} />;
  }

  return (
    <div className="h-full overflow-y-auto p-8 custom-scrollbar">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Statistiques des 30 derniers jours</p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Conversations"
            value={analytics?.total_conversations || 0}
            icon={MessageSquare}
            colorClass="bg-primary/10 text-primary"
          />
          <StatCard
            title="Feedbacks"
            value={analytics?.total_feedbacks || 0}
            icon={ThumbsUp}
            colorClass="bg-success/10 text-success"
          />
          <StatCard
            title="Score Moyen"
            value={analytics?.average_score?.toFixed(1) || "N/A"}
            icon={BarChart3}
            colorClass="bg-accent text-accent-foreground"
          />
          <StatCard
            title="En attente"
            value={analytics?.pending_training || 0}
            icon={BookOpen}
            colorClass="bg-warning/10 text-warning"
          />
        </div>

        {/* Usage & Consumption Dashboard */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <UsageDashboard refetchInterval={30000} />
          
          {/* Score Distribution Chart */}
          {analytics?.score_distribution ? (
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
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
