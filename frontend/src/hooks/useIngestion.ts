/**
 * Hooks personnalisés pour l'ingestion de documents
 * Utilise React Query mutations avec gestion d'erreurs centralisée
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { IngestResponse } from "@/types/api";

// ===== Types =====

interface TextIngestionData {
  content: string;
  title?: string;
}

interface GithubIngestionData {
  repository: string;
  branch?: string;
}

interface IngestionResult {
  success: boolean;
  message: string;
  chunks_created?: number;
}

// ===== Text Ingestion =====

export function useTextIngestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TextIngestionData): Promise<IngestResponse> => {
      return api.ingestText({
        content: data.content,
        source_id: `manual:${Date.now()}`,
        title: data.title,
      });
    },
    onMutate: () => {
      // Afficher un toast de chargement
      return {
        toastId: toast.loading("Ingestion en cours...", {
          description: "Traitement de votre texte",
        }),
      };
    },
    onSuccess: (data, variables, context) => {
      toast.success("Texte ingéré avec succès", {
        id: context?.toastId,
        description: data.message || `${variables.title || "Document"} ajouté à la base de connaissances`,
      });

      // Invalider le cache des documents si on en avait un
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error, _variables, context) => {
      toast.error("Échec de l'ingestion", {
        id: context?.toastId,
        description: error instanceof Error ? error.message : "Impossible d'ingérer le texte",
      });
    },
  });
}

// ===== PDF Ingestion =====

export function usePdfIngestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File): Promise<IngestResponse> => {
      return api.ingestPdf(file);
    },
    onMutate: (file) => {
      return {
        toastId: toast.loading("Upload en cours...", {
          description: `Traitement de ${file.name}`,
        }),
        fileName: file.name,
      };
    },
    onSuccess: (data, _file, context) => {
      toast.success("PDF importé avec succès", {
        id: context?.toastId,
        description: data.message || `${context?.fileName} ajouté à la base de connaissances`,
      });

      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error, _file, context) => {
      toast.error("Échec de l'upload", {
        id: context?.toastId,
        description: error instanceof Error ? error.message : "Impossible de traiter le PDF",
      });
    },
  });
}

// ===== GitHub Ingestion =====

export function useGithubIngestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: GithubIngestionData): Promise<IngestResponse> => {
      return api.ingestGithub({
        repositories: [data.repository],
      });
    },
    onMutate: (data) => {
      return {
        toastId: toast.loading("Import GitHub en cours...", {
          description: `Indexation de ${data.repository}`,
        }),
        repository: data.repository,
      };
    },
    onSuccess: (data, _variables, context) => {
      toast.success("Repository importé", {
        id: context?.toastId,
        description: data.message || `${context?.repository} ajouté à la base de connaissances`,
      });

      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error, _variables, context) => {
      toast.error("Échec de l'import GitHub", {
        id: context?.toastId,
        description: error instanceof Error 
          ? error.message 
          : "Repository introuvable ou accès refusé",
      });
    },
  });
}

// ===== Combined Hook =====

/**
 * Hook combiné pour toutes les opérations d'ingestion
 */
export function useIngestion() {
  const textMutation = useTextIngestion();
  const pdfMutation = usePdfIngestion();
  const githubMutation = useGithubIngestion();

  return {
    ingestText: textMutation.mutateAsync,
    ingestPdf: pdfMutation.mutateAsync,
    ingestGithub: githubMutation.mutateAsync,
    isLoading: textMutation.isPending || pdfMutation.isPending || githubMutation.isPending,
    textStatus: textMutation,
    pdfStatus: pdfMutation,
    githubStatus: githubMutation,
  };
}
