/**
 * Types pour l'API RAG Agent
 */

// ===== Query Types =====

export interface QueryRequest {
  question: string;
  session_id?: string;
  system_prompt?: string;
  use_web_search?: boolean;
  use_rag?: boolean;
  enable_reflection?: boolean;
  stream?: boolean;
  provider?: string;
  model?: string;
}

export interface Source {
  source_type: "vector_store" | "perplexity";
  content_preview: string;
  similarity_score: number | null;
  url: string | null;
  document_id?: string; // ID du document source (pour vector_store)
}

export interface RoutingInfo {
  intent: "general" | "documents" | "web_search" | "hybrid" | "greeting";
  use_rag: boolean;
  use_web: boolean;
  confidence: number;
  reasoning: string;
  latency_ms: number;
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
    model_used?: string;
    routing_intent?: string;
    routing_confidence?: number;
    routing_latency_ms?: number;
  };
  thought_process?: string;
  routing?: RoutingInfo;
}

// ===== Streaming Types =====

export type StreamEventType = 
  | "routing"
  | "search_start"
  | "search_complete"
  | "generation_start"
  | "chunk"
  | "thought"
  | "complete"
  | "error";

export interface StreamEvent {
  event: StreamEventType;
  data: Record<string, unknown>;
}

export interface RoutingEvent {
  status: "started" | "completed";
  intent?: string;
  use_rag?: boolean;
  use_web?: boolean;
  confidence?: number;
}

export interface SearchEvent {
  type: "rag" | "web";
  results?: number;
  found?: boolean;
}

export interface ChunkEvent {
  content: string;
}

export interface ThoughtEvent {
  content: string;
}

export interface CompleteEvent {
  conversation_id: string | null;
  sources: Source[];
  metadata: Record<string, unknown>;
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
  agent_id?: string;
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
  // Agent info
  agent_id?: string;
  agent_name?: string;
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
  // Nouvelles propriétés
  thoughtProcess?: string;
  routingInfo?: RoutingInfo;
  streamingSteps?: StreamingStep[];
}

export interface StreamingStep {
  type: "routing" | "search_rag" | "search_web" | "generating";
  status: "pending" | "in_progress" | "completed";
  label: string;
  details?: string;
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
  
  // BYOK Provider Keys Summary
  provider_keys_summary?: Record<string, boolean>;
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

// ===== Agent Types =====

export interface AgentInfo {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  model_id: string;
  system_prompt: string | null;
  temperature: number;
  rag_enabled: boolean;
  max_monthly_tokens: number;
  max_daily_requests: number;
  tokens_used_this_month: number;
  requests_today: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  api_keys_count?: number;
  documents_count?: number;
}

export interface AgentCreate {
  name: string;
  description?: string;
  model_id?: string;
  system_prompt?: string;
  temperature?: number;
  rag_enabled?: boolean;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  model_id?: string;
  system_prompt?: string;
  temperature?: number;
  rag_enabled?: boolean;
  is_active?: boolean;
}
