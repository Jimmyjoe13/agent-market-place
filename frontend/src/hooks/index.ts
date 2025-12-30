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
