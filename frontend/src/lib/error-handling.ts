/**
 * Gestion des erreurs API centralisée
 * Inclut la gestion du Rate Limiting (429)
 */

import { toast } from "sonner";

// ===== Types =====

export interface ApiError {
  status: number;
  message: string;
  retryAfter?: number;
  details?: Record<string, unknown>;
}

export interface RateLimitInfo {
  isRateLimited: boolean;
  retryAfter: number;
  retryAt: Date | null;
}

// ===== Rate Limit State =====

let rateLimitState: RateLimitInfo = {
  isRateLimited: false,
  retryAfter: 0,
  retryAt: null,
};

let rateLimitTimer: ReturnType<typeof setTimeout> | null = null;

// ===== Functions =====

/**
 * Parse une erreur API et retourne un objet ApiError structuré
 */
export function parseApiError(error: unknown): ApiError {
  if (error instanceof Response) {
    return {
      status: error.status,
      message: getStatusMessage(error.status),
      retryAfter: parseRetryAfter(error.headers.get("Retry-After")),
    };
  }

  if (error && typeof error === "object" && "response" in error) {
    const axiosError = error as { response?: { status: number; headers?: Record<string, string>; data?: { detail?: string } } };
    const status = axiosError.response?.status || 500;
    const retryAfter = parseRetryAfter(axiosError.response?.headers?.["retry-after"]);
    
    return {
      status,
      message: axiosError.response?.data?.detail || getStatusMessage(status),
      retryAfter,
    };
  }

  if (error instanceof Error) {
    return {
      status: 0,
      message: error.message,
    };
  }

  return {
    status: 0,
    message: "Une erreur inconnue est survenue",
  };
}

/**
 * Parse le header Retry-After
 */
function parseRetryAfter(value: string | null | undefined): number | undefined {
  if (!value) return undefined;
  
  const seconds = parseInt(value, 10);
  if (!isNaN(seconds)) return seconds;
  
  // Essayer de parser comme date
  const date = new Date(value);
  if (!isNaN(date.getTime())) {
    return Math.max(0, Math.ceil((date.getTime() - Date.now()) / 1000));
  }
  
  return undefined;
}

/**
 * Retourne un message user-friendly basé sur le status HTTP
 */
function getStatusMessage(status: number): string {
  const messages: Record<number, string> = {
    400: "Requête invalide. Vérifiez vos données.",
    401: "Non autorisé. Vérifiez votre clé API.",
    403: "Accès refusé. Permissions insuffisantes.",
    404: "Ressource introuvable.",
    408: "La requête a expiré. Réessayez.",
    429: "Trop de requêtes. Veuillez patienter.",
    500: "Erreur serveur. Réessayez plus tard.",
    502: "Service temporairement indisponible.",
    503: "Service en maintenance. Réessayez plus tard.",
    504: "Le serveur ne répond pas. Vérifiez votre connexion.",
  };

  return messages[status] || `Erreur ${status}`;
}

/**
 * Gère une erreur de Rate Limiting
 */
export function handleRateLimitError(retryAfter: number = 60): void {
  const retryAt = new Date(Date.now() + retryAfter * 1000);
  
  rateLimitState = {
    isRateLimited: true,
    retryAfter,
    retryAt,
  };

  // Clear le timer existant
  if (rateLimitTimer) {
    clearTimeout(rateLimitTimer);
  }

  // Afficher un toast avec compte à rebours
  const toastId = toast.warning("Limite de requêtes atteinte", {
    description: `Veuillez patienter ${retryAfter} secondes...`,
    duration: retryAfter * 1000,
  });

  // Mettre à jour le toast avec le compte à rebours
  let remaining = retryAfter;
  const countdownInterval = setInterval(() => {
    remaining--;
    if (remaining > 0) {
      toast.warning("Limite de requêtes atteinte", {
        id: toastId,
        description: `Veuillez patienter ${remaining} secondes...`,
        duration: remaining * 1000,
      });
    } else {
      clearInterval(countdownInterval);
    }
  }, 1000);

  // Reset après le délai
  rateLimitTimer = setTimeout(() => {
    rateLimitState = {
      isRateLimited: false,
      retryAfter: 0,
      retryAt: null,
    };
    
    clearInterval(countdownInterval);
    
    toast.success("Vous pouvez reprendre", {
      id: toastId,
      description: "La limite de requêtes a été réinitialisée.",
    });
  }, retryAfter * 1000);
}

/**
 * Vérifie si on est actuellement rate limited
 */
export function isRateLimited(): boolean {
  return rateLimitState.isRateLimited;
}

/**
 * Retourne les infos de rate limiting actuelles
 */
export function getRateLimitInfo(): RateLimitInfo {
  return { ...rateLimitState };
}

/**
 * Gère une erreur API de manière centralisée
 */
export function handleApiError(error: unknown, context?: string): ApiError {
  const apiError = parseApiError(error);

  // Gestion spéciale pour 429
  if (apiError.status === 429) {
    handleRateLimitError(apiError.retryAfter);
    return apiError;
  }

  // Gestion pour 401 (non autorisé)
  if (apiError.status === 401) {
    toast.error("Session expirée", {
      description: "Veuillez reconfigurer votre clé API.",
      action: {
        label: "Paramètres",
        onClick: () => window.location.href = "/settings",
      },
    });
    return apiError;
  }

  // Log en dev
  if (process.env.NODE_ENV !== "production") {
    console.error(`[API Error${context ? ` - ${context}` : ""}]`, apiError);
  }

  return apiError;
}

/**
 * Wrapper pour les appels API avec gestion d'erreurs automatique
 */
export async function withErrorHandling<T>(
  apiCall: () => Promise<T>,
  context?: string
): Promise<T> {
  // Vérifier le rate limiting avant l'appel
  if (isRateLimited()) {
    const info = getRateLimitInfo();
    throw new Error(`Rate limited. Retry after ${info.retryAfter} seconds.`);
  }

  try {
    return await apiCall();
  } catch (error) {
    handleApiError(error, context);
    throw error;
  }
}
