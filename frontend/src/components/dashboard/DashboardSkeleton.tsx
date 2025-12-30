/**
 * Dashboard Skeletons
 * ===================
 * 
 * Composants skeleton pour les états de chargement du dashboard.
 * Imitent la structure finale pour une meilleure UX perçue.
 */

"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton pour une carte de statistique individuelle
 */
export function StatCardSkeleton() {
  return (
    <Card className="border-border bg-card">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16" />
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton pour le graphique de distribution des scores
 */
export function ChartSkeleton() {
  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>
        <div className="flex h-32 items-end gap-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-2">
              <Skeleton 
                className="w-full rounded-t" 
                style={{ height: `${20 + Math.random() * 60}%` }} 
              />
              <Skeleton className="h-4 w-8" />
              <Skeleton className="h-3 w-6" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Skeleton complet pour la page Dashboard
 * Reproduit exactement la structure de la page finale
 */
export function DashboardSkeleton() {
  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="mx-auto max-w-6xl">
        {/* Header Skeleton */}
        <div className="mb-8">
          <Skeleton className="h-8 w-40 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>

        {/* Stats Grid Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>

        {/* Chart Skeleton */}
        <div className="mt-8">
          <ChartSkeleton />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton générique pour une liste de cards
 */
export function CardListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {[...Array(count)].map((_, i) => (
        <Card key={i} className="border-border bg-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-3 w-2/3" />
              </div>
              <Skeleton className="h-8 w-20" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Skeleton pour une table de données
 */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-muted/50 p-3 flex gap-4">
        {[...Array(cols)].map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {[...Array(rows)].map((_, rowIdx) => (
        <div key={rowIdx} className="p-3 flex gap-4 border-t border-border">
          {[...Array(cols)].map((_, colIdx) => (
            <Skeleton key={colIdx} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export default DashboardSkeleton;
