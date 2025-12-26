/**
 * Types pour l'API RAG Agent
 */

// ===== Query Types =====

export interface QueryRequest {
  question: string;
  session_id?: string;
  system_prompt?: string;
  use_web_search?: boolean;
}

export interface Source {
  source_type: "vector_store" | "perplexity";
  content_preview: string;
  similarity_score: number | null;
  url: string | null;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  conversation_id: string;
  session_id: string;
  metadata: {
    elapsed_ms: number;
    tokens_input: number;
    tokens_output: number;
    vector_results: number;
    web_search_used: boolean;
  };
}

// ===== Feedback Types =====

export interface FeedbackRequest {
  conversation_id: string;
  score: number;
  comment?: string;
  flag_for_training?: boolean;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
}

// ===== Ingestion Types =====

export interface IngestTextRequest {
  content: string;
  source_id: string;
  title?: string;
  tags?: string[];
}

export interface IngestGithubRequest {
  repositories: string[];
  skip_duplicates?: boolean;
}

export interface IngestResponse {
  success: boolean;
  documents_created: number;
  documents_skipped: number;
  errors: number;
  message: string;
}

// ===== API Keys Types =====

export interface ApiKeyCreate {
  name: string;
  scopes: (string | "query" | "ingest" | "feedback" | "admin")[];
  rate_limit_per_minute?: number;
  monthly_quota?: number;
  expires_in_days?: number;
  metadata?: Record<string, unknown>;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  key?: string; // Only on creation
  prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  monthly_quota: number;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  rate_limit_per_minute: number;
  monthly_quota: number;
  monthly_usage: number;
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

// ===== Analytics Types =====

export interface AnalyticsResponse {
  total_conversations: number;
  total_feedbacks: number;
  average_score: number;
  pending_training: number;
  score_distribution: Record<string, number>;
}

// ===== Chat UI Types =====

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Source[];
  conversationId?: string;
  isLoading?: boolean;
}

export interface ChatSession {
  id: string;
  messages: Message[];
  createdAt: Date;
}

// ===== User & Subscription Types =====

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: "user" | "admin" | "superadmin";
  
  // Subscription Info
  plan_slug: string;
  plan_name: string;
  subscription_status: string;
  
  // Usage
  requests_used: number;
  requests_limit: number;
  documents_used: number;
  documents_limit: number;
  api_keys_used: number;
  api_keys_limit: number;
}

export interface Plan {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  price_monthly_cents: number;
  price_yearly_cents: number;
  requests_per_month: number;
  features: string[];
  is_active: boolean;
}

export interface Subscription {
  id: string;
  plan_id: string;
  status: string;
  current_period_end: string;
  plan: Plan;
}

