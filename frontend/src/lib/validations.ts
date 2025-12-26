/**
 * Schémas de validation Zod pour l'application
 * Ces schémas sont synchronisés avec les modèles Pydantic du backend
 */

import { z } from "zod";

// ===== API Key Schemas =====

export const apiKeySchema = z.object({
  key: z
    .string()
    .min(1, "La clé API est requise")
    .regex(/^rag_[a-zA-Z0-9]+$/, "Format de clé invalide (doit commencer par 'rag_')"),
});

export const apiKeyCreateSchema = z.object({
  name: z
    .string()
    .min(2, "Le nom doit contenir au moins 2 caractères")
    .max(50, "Le nom ne peut pas dépasser 50 caractères"),
  scopes: z
    .array(z.enum(["query", "ingest", "feedback", "admin"]))
    .min(1, "Au moins un scope est requis"),
  expires_in_days: z
    .number()
    .int()
    .min(1, "Minimum 1 jour")
    .max(365, "Maximum 365 jours")
    .optional(),
});

export type ApiKeyFormData = z.infer<typeof apiKeySchema>;
export type ApiKeyCreateFormData = z.infer<typeof apiKeyCreateSchema>;

// ===== Document Ingestion Schemas =====

export const textIngestionSchema = z.object({
  title: z
    .string()
    .max(200, "Le titre ne peut pas dépasser 200 caractères")
    .optional()
    .or(z.literal("")),
  content: z
    .string()
    .min(10, "Le contenu doit contenir au moins 10 caractères")
    .max(500000, "Le contenu est trop volumineux (max 500 000 caractères)"),
});

export const githubIngestionSchema = z.object({
  repository: z
    .string()
    .min(1, "Le repository est requis")
    .regex(
      /^[\w.-]+\/[\w.-]+$/,
      "Format invalide. Utilisez 'owner/repository' (ex: facebook/react)"
    ),
  branch: z
    .string()
    .max(100, "Le nom de branche est trop long")
    .optional(),
});

export const pdfIngestionSchema = z.object({
  file: z
    .instanceof(File, { message: "Veuillez sélectionner un fichier" })
    .refine((file) => file.size <= 50 * 1024 * 1024, "Le fichier est trop volumineux (max 50 Mo)")
    .refine(
      (file) => file.type === "application/pdf",
      "Seuls les fichiers PDF sont acceptés"
    ),
});

export type TextIngestionFormData = z.infer<typeof textIngestionSchema>;
export type GithubIngestionFormData = z.infer<typeof githubIngestionSchema>;
export type PdfIngestionFormData = z.infer<typeof pdfIngestionSchema>;

// ===== Query Schemas =====

export const querySchema = z.object({
  question: z
    .string()
    .min(3, "La question doit contenir au moins 3 caractères")
    .max(2000, "La question est trop longue (max 2000 caractères)"),
  useWebSearch: z.boolean().default(true),
});

export type QueryFormData = z.infer<typeof querySchema>;

// ===== Feedback Schemas =====

export const feedbackSchema = z.object({
  score: z.number().int().min(1).max(5),
  comment: z
    .string()
    .max(1000, "Le commentaire est trop long")
    .optional()
    .or(z.literal("")),
});

export type FeedbackFormData = z.infer<typeof feedbackSchema>;

/**
 * Valide les données avec un schéma et retourne les erreurs formatées
 */
export function validateWithSchema<T>(
  schema: z.ZodSchema<T>,
  data: unknown
): { success: true; data: T } | { success: false; errors: Record<string, string> } {
  const result = schema.safeParse(data);
  
  if (result.success) {
    return { success: true, data: result.data };
  }
  
  const errors: Record<string, string> = {};
  result.error.issues.forEach((issue) => {
    const path = issue.path.join(".");
    errors[path] = issue.message;
  });
  
  return { success: false, errors };
}
