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
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 120000, 
    });

    // Initialiser la clé depuis le stockage local si disponible
    this.apiKey = this.getStoredApiKey();

    // Interceptor pour ajouter l'auth
    this.client.interceptors.request.use((config) => {
      // 1. Rate Limiting Check
      if (isRateLimited()) {
        const info = getRateLimitInfo();
        const error = new Error(`Rate limited. Retry after ${info.retryAfter} seconds.`);
        error.name = "RateLimitError";
        return Promise.reject(error);
      }

      // 2. Auth Console (Session Token)
      // Priorité: Token passé explicitement dans config > Token stocké
      const token = config.headers["Authorization"] || (this.accessToken ? `Bearer ${this.accessToken}` : null);
      if (token && typeof token === 'string' && token.startsWith('Bearer ')) {
        config.headers["Authorization"] = token;
      }

      // 3. Auth RAG (API Key)
      // Priorité: Clé passée explicitement > Clé stockée
      const key = config.headers["X-API-Key"] || this.apiKey;
      if (key) {
        config.headers["X-API-Key"] = key;
      }

      return config;
    });

    // Interceptor Response (inchangé sauf 401 sur token)
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const status = error.response?.status;

        // Rate Limit
        if (status === 429) {
          const retryAfter = parseInt(
            error.response?.headers?.["retry-after"] || "60",
            10
          );
          handleRateLimitError(retryAfter);
        }

        return Promise.reject(error);
      }
    );
  }

  // ===== Auth State Management =====

  getStoredApiKey(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("rag_api_key");
  }

  setApiKey(key: string) {
    this.apiKey = key;
    if (typeof window !== "undefined") {
      localStorage.setItem("rag_api_key", key);
    }
  }

  clearApiKey() {
    this.apiKey = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("rag_api_key");
    }
  }

  setAccessToken(token: string) {
    this.accessToken = token;
  }

  hasApiKey(): boolean {
    return !!this.apiKey;
  }

  // ===== Console Endpoints (User) =====

  async getUserProfile(): Promise<any> {
    const { data } = await this.client.get("/auth/me");
    return data;
  }

  async getPlans(): Promise<any[]> {
    const { data } = await this.client.get("/auth/plans");
    return data;
  }

  async updateProfile(data: { name?: string; avatar_url?: string; provider_keys?: Record<string, string> }): Promise<any> {
    const { data: updated } = await this.client.patch("/auth/me", data);
    return updated;
  }

  async getUserApiKeys(): Promise<{ keys: ApiKeyInfo[]; total: number }> {
    const { data } = await this.client.get("/console/keys");
    return data;
  }

  async createUserApiKey(request: ApiKeyCreate): Promise<ApiKeyResponse> {
    const { data } = await this.client.post("/console/keys", request);
    return data;
  }

  async revokeUserApiKey(keyId: string): Promise<void> {
    await this.client.delete(`/console/keys/${keyId}`);
  }

  // Support anciens noms (backward compatibility)
  async listApiKeys(masterKey?: string): Promise<{ keys: ApiKeyInfo[]; total: number }> {
    return this.getUserApiKeys();
  }

  async createApiKey(request: ApiKeyCreate, masterKey?: string): Promise<ApiKeyResponse> {
    return this.createUserApiKey(request);
  }

  async revokeApiKey(keyId: string, masterKey?: string): Promise<void> {
    return this.revokeUserApiKey(keyId);
  }

  async getUserUsage(): Promise<any> {
    const { data } = await this.client.get("/console/usage");
    return data;
  }

  // ===== Query Endpoints (Legacy & RAG) =====

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

  // ===== Health Check =====

  async healthCheck(): Promise<{ status: string; version: string }> {
    const { data } = await this.client.get<{ status: string; version: string }>("/health", {
      baseURL: API_BASE_URL.replace("/api/v1", ""),
    });
    return data;
  }

  // ===== Agent Config Endpoints =====

  async getAgentConfig(): Promise<{
    agent_id: string;
    config: {
      model_id: string;
      system_prompt: string | null;
      rag_enabled: boolean;
      agent_name: string | null;
    };
  }> {
    const { data } = await this.client.get("/agent/config");
    return data;
  }

  async updateAgentConfig(config: {
    model_id?: string;
    system_prompt?: string;
    rag_enabled?: boolean;
    agent_name?: string;
  }): Promise<{
    agent_id: string;
    config: {
      model_id: string;
      system_prompt: string | null;
      rag_enabled: boolean;
      agent_name: string | null;
    };
  }> {
    const { data } = await this.client.patch("/agent/config", config);
    return data;
  }

  async getAvailableModels(): Promise<{
    models: Array<{
      id: string;
      provider: string;
      name: string;
      description?: string;
      recommended?: boolean;
      premium?: boolean;
      new?: boolean;
    }>;
  }> {
    const { data } = await this.client.get("/agent/available-models");
    return data;
  }
}

// ===== Export Singleton =====

export const api = new ApiClient();
export default api;
