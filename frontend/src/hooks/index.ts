/**
 * Export centralisé de tous les hooks personnalisés
 */

// Chat
export { useChat } from "./useChat";

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

