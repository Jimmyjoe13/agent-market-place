import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

interface CreateJobRequest {
  content: string;
  source_filename: string;
  source_type?: string;
  webhook_url?: string;
}

interface CreateJobResponse {
  job_id: string;
  status: string;
  message: string;
}

interface JobListResponse {
  jobs: DocumentJob[];
  total: number;
}

/**
 * Hook pour créer un job d'ingestion de document.
 */
export function useCreateDocumentJob(apiKey: string) {
  const queryClient = useQueryClient();

  return useMutation<CreateJobResponse, Error, CreateJobRequest>({
    mutationFn: async (request) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/ingest`, {
        method: "POST",
        headers: {
          "X-API-Key": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || "Erreur lors de la création du job");
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalider la liste des jobs
      queryClient.invalidateQueries({ queryKey: ["document-jobs"] });
    },
  });
}

/**
 * Hook pour récupérer le statut d'un job.
 */
export function useDocumentJob(
  jobId: string,
  apiKey: string,
  options?: { refetchInterval?: number | false }
) {
  return useQuery<DocumentJob>({
    queryKey: ["document-job", jobId],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error("Impossible de récupérer le statut du job");
      }

      return response.json();
    },
    enabled: !!jobId && !!apiKey,
    refetchInterval: options?.refetchInterval,
  });
}

/**
 * Hook pour lister les jobs d'un agent.
 */
export function useDocumentJobs(
  apiKey: string,
  options?: {
    status?: string;
    limit?: number;
    offset?: number;
  }
) {
  const { status, limit = 20, offset = 0 } = options || {};

  return useQuery<JobListResponse>({
    queryKey: ["document-jobs", status, limit, offset],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (status) {
        params.set("status", status);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/jobs?${params}`,
        { headers: { "X-API-Key": apiKey } }
      );

      if (!response.ok) {
        throw new Error("Impossible de récupérer la liste des jobs");
      }

      return response.json();
    },
    enabled: !!apiKey,
    refetchInterval: 5000, // Actualiser toutes les 5s
  });
}

/**
 * Hook pour annuler un job.
 */
export function useCancelDocumentJob(apiKey: string) {
  const queryClient = useQueryClient();

  return useMutation<{ message: string }, Error, string>({
    mutationFn: async (jobId) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
        method: "DELETE",
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error("Impossible d'annuler le job");
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-jobs"] });
    },
  });
}

export default useDocumentJobs;
