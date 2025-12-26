/**
 * Client API pour RAG Agent
 * Avec gestion centralisée des erreurs et rate limiting
 */

import axios, { AxiosInstance, AxiosError } from "axios";
import { handleRateLimitError, isRateLimited, getRateLimitInfo } from "./error-handling";
import type {
  QueryRequest,
  QueryResponse,
  FeedbackRequest,
  FeedbackResponse,
  IngestTextRequest,
  IngestGithubRequest,
  IngestResponse,
  ApiKeyCreate,
  ApiKeyResponse,
  ApiKeyInfo,
  AnalyticsResponse,
} from "@/types/api";

// ===== Configuration =====

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ===== API Client =====

class ApiClient {
  private client: AxiosInstance;
  private apiKey: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 30000, // 30 secondes
    });

    // Interceptor pour ajouter la clé API et vérifier le rate limiting
    this.client.interceptors.request.use((config) => {
      // Vérifier le rate limiting avant chaque requête
      if (isRateLimited()) {
        const info = getRateLimitInfo();
        const error = new Error(`Rate limited. Retry after ${info.retryAfter} seconds.`);
        error.name = "RateLimitError";
        return Promise.reject(error);
      }

      const key = this.apiKey || this.getStoredApiKey();
      if (key) {
        config.headers["X-API-Key"] = key;
      }
      return config;
    });

    // Interceptor pour gérer les erreurs
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const status = error.response?.status;

        // Gestion du rate limiting (429)
        if (status === 429) {
          const retryAfter = parseInt(
            error.response?.headers?.["retry-after"] || "60",
            10
          );
          handleRateLimitError(retryAfter);
        }

        // Clé invalide (401)
        if (status === 401) {
          this.clearApiKey();
        }

        return Promise.reject(error);
      }
    );
  }

  // ===== API Key Management =====

  setApiKey(key: string) {
    this.apiKey = key;
    if (typeof window !== "undefined") {
      localStorage.setItem("rag_api_key", key);
    }
  }

  getStoredApiKey(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("rag_api_key");
    }
    return null;
  }

  clearApiKey() {
    this.apiKey = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("rag_api_key");
    }
  }

  hasApiKey(): boolean {
    return !!(this.apiKey || this.getStoredApiKey());
  }

  // ===== Query Endpoints =====

  async query(request: QueryRequest): Promise<QueryResponse> {
    const { data } = await this.client.post<QueryResponse>("/query", request);
    return data;
  }

  async newSession(): Promise<{ session_id: string }> {
    const { data } = await this.client.post<{ session_id: string }>("/session/new");
    return data;
  }

  // ===== Feedback Endpoints =====

  async submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
    const { data } = await this.client.post<FeedbackResponse>("/feedback", request);
    return data;
  }

  async getAnalytics(days = 30): Promise<AnalyticsResponse> {
    const { data } = await this.client.get<AnalyticsResponse>(`/analytics?days=${days}`);
    return data;
  }

  // ===== Ingestion Endpoints =====

  async ingestText(request: IngestTextRequest): Promise<IngestResponse> {
    const { data } = await this.client.post<IngestResponse>("/ingest/text", request);
    return data;
  }

  async ingestGithub(request: IngestGithubRequest): Promise<IngestResponse> {
    const { data } = await this.client.post<IngestResponse>("/ingest/github", request);
    return data;
  }

  async ingestPdf(file: File): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await this.client.post<IngestResponse>("/ingest/pdf", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  }

  // ===== API Keys Endpoints (Admin) =====

  async createApiKey(request: ApiKeyCreate, masterKey: string): Promise<ApiKeyResponse> {
    const { data } = await this.client.post<ApiKeyResponse>("/keys", request, {
      headers: { "X-API-Key": masterKey },
    });
    return data;
  }

  async listApiKeys(masterKey: string): Promise<{ keys: ApiKeyInfo[]; total: number }> {
    const { data } = await this.client.get<{ keys: ApiKeyInfo[]; total: number }>("/keys", {
      headers: { "X-API-Key": masterKey },
    });
    return data;
  }

  async revokeApiKey(keyId: string, masterKey: string): Promise<void> {
    await this.client.delete(`/keys/${keyId}`, {
      headers: { "X-API-Key": masterKey },
    });
  }

  // ===== Health Check =====

  async healthCheck(): Promise<{ status: string; version: string }> {
    const { data } = await this.client.get<{ status: string; version: string }>("/health", {
      baseURL: API_BASE_URL.replace("/api/v1", ""),
    });
    return data;
  }
}

// ===== Export Singleton =====

export const api = new ApiClient();
export default api;
