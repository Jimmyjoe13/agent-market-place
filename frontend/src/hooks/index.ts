/**
 * Export centralisé de tous les hooks personnalisés
 */

// Chat
export { useChat } from "./useChat";
export { useStreamingChat } from "./useStreamingChat";
export { useUnifiedChat } from "./useUnifiedChat";

// API Health
export { useApiHealth, useApiStatus } from "./useApiHealth";

// Ingestion
export {
  useTextIngestion,
  usePdfIngestion,
  useGithubIngestion,
  useIngestion,
} from "./useIngestion";

// API Keys
export {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  useApiKeysManager,
  apiKeysQueryKey,
} from "./useApiKeys";

// Rate Limiting
export { useRateLimit } from "./useRateLimit";

// Document Jobs
export {
  useCreateDocumentJob,
  useDocumentJob,
  useDocumentJobs,
  useCancelDocumentJob,
} from "./useDocumentJobs";

// Budget & Key Management
export {
  useBudgetLimits,
  useUpdateBudgetLimits,
  useUsageStats,
  useRotateKey,
} from "./useBudgetLimits";

// Panel State (Playground)
export { usePanelState } from "./usePanelState";

// User Usage Dashboard
export {
  useUserUsage,
  calculateUsagePercentages,
  getUsageColor,
  getProgressColor,
  type UserUsage,
  type UsagePercentages,
} from "./useUserUsage";

// Realtime Usage (Supabase Realtime)
export {
  useRealtimeUsage,
  calculateUsagePercentages as calculateRealtimeUsagePercentages,
  getUsageColor as getRealtimeUsageColor,
  getProgressColor as getRealtimeProgressColor,
  type UserUsage as RealtimeUserUsage,
  type UsagePercentages as RealtimeUsagePercentages,
  type ConnectionStatus,
  type RealtimeUsageResult,
} from "./useRealtimeUsage";

