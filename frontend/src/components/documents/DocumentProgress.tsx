"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, CheckCircle, XCircle, Clock, FileText } from "lucide-react";

// Types
interface DocumentJob {
  id: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress: number;
  chunks_total: number;
  chunks_processed: number;
  source_filename: string;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

// Status labels and colors
const STATUS_CONFIG = {
  pending: {
    label: "En attente",
    color: "bg-yellow-500",
    icon: Clock,
  },
  processing: {
    label: "Traitement en cours",
    color: "bg-blue-500",
    icon: Loader2,
  },
  completed: {
    label: "Terminé",
    color: "bg-green-500",
    icon: CheckCircle,
  },
  failed: {
    label: "Échec",
    color: "bg-red-500",
    icon: XCircle,
  },
  cancelled: {
    label: "Annulé",
    color: "bg-gray-500",
    icon: XCircle,
  },
};

interface DocumentProgressProps {
  jobId: string;
  apiKey: string;
  apiBaseUrl?: string;
  onComplete?: (job: DocumentJob) => void;
  onError?: (error: Error) => void;
}

/**
 * Composant de suivi de progression d'ingestion de document.
 * 
 * Affiche une barre de progression avec le statut du job,
 * et poll automatiquement pendant le traitement.
 */
export function DocumentProgress({
  jobId,
  apiKey,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  onComplete,
  onError,
}: DocumentProgressProps) {
  const [isPolling, setIsPolling] = useState(true);

  // Query pour récupérer le statut du job
  const { data: job, isLoading, error } = useQuery<DocumentJob>({
    queryKey: ["document-job", jobId],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`, {
        headers: {
          "X-API-Key": apiKey,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch job status");
      }

      return response.json();
    },
    // Poll toutes les secondes pendant le traitement
    refetchInterval: isPolling ? 1000 : false,
    enabled: !!jobId && !!apiKey,
  });

  // Arrêter le polling quand le job est terminé
  useEffect(() => {
    if (job) {
      if (job.status === "completed" || job.status === "failed" || job.status === "cancelled") {
        setIsPolling(false);

        if (job.status === "completed" && onComplete) {
          onComplete(job);
        }
      }
    }
  }, [job, onComplete]);

  // Gérer les erreurs
  useEffect(() => {
    if (error && onError) {
      onError(error as Error);
    }
  }, [error, onError]);

  if (isLoading && !job) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Chargement...</span>
      </div>
    );
  }

  if (!job) {
    return null;
  }

  const statusConfig = STATUS_CONFIG[job.status];
  const StatusIcon = statusConfig.icon;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">
              {job.source_filename}
            </CardTitle>
          </div>
          <Badge 
            variant="outline" 
            className={`${statusConfig.color} text-white border-0`}
          >
            <StatusIcon className={`h-3 w-3 mr-1 ${job.status === "processing" ? "animate-spin" : ""}`} />
            {statusConfig.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Barre de progression */}
        <div className="space-y-1">
          <Progress value={job.progress} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{job.progress}%</span>
            <span>
              {job.chunks_processed} / {job.chunks_total || "?"} chunks
            </span>
          </div>
        </div>

        {/* Message d'erreur */}
        {job.status === "failed" && job.error_message && (
          <Alert variant="destructive">
            <AlertDescription className="text-sm">
              {job.error_message}
            </AlertDescription>
          </Alert>
        )}

        {/* Temps estimé */}
        {job.status === "processing" && job.chunks_total > 0 && (
          <p className="text-xs text-muted-foreground">
            Temps restant estimé: ~{Math.ceil((job.chunks_total - job.chunks_processed) * 0.5)}s
          </p>
        )}
      </CardContent>
    </Card>
  );
}

interface DocumentJobListProps {
  apiKey: string;
  apiBaseUrl?: string;
  limit?: number;
}

/**
 * Liste des jobs d'ingestion récents.
 */
export function DocumentJobList({
  apiKey,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  limit = 5,
}: DocumentJobListProps) {
  const { data, isLoading } = useQuery<{ jobs: DocumentJob[]; total: number }>({
    queryKey: ["document-jobs", limit],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/api/v1/jobs?limit=${limit}`, {
        headers: {
          "X-API-Key": apiKey,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch jobs");
      }

      return response.json();
    },
    enabled: !!apiKey,
    refetchInterval: 5000, // Refresh toutes les 5 secondes
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data?.jobs?.length) {
    return (
      <div className="text-center text-muted-foreground p-4">
        Aucun document en cours d'ingestion
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {data.jobs.map((job) => (
        <DocumentProgress
          key={job.id}
          jobId={job.id}
          apiKey={apiKey}
          apiBaseUrl={apiBaseUrl}
        />
      ))}
    </div>
  );
}

export default DocumentProgress;
