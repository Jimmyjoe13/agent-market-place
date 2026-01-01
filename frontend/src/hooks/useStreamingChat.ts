/**
 * Hook pour la gestion du streaming SSE (Server-Sent Events) - V2
 * 
 * Améliorations :
 * - Timeout configurable avec indicateur visuel
 * - Reconnexion automatique en cas de coupure réseau
 * - Retry avec backoff exponentiel
 * - Affichage des sources en temps réel
 */

"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";
import type { 
  Message, 
  Source, 
  StreamEventType, 
  StreamingStep, 
  RoutingInfo 
} from "@/types/api";

// ===== Types =====

interface StreamState {
  isStreaming: boolean;
  currentContent: string;
  currentThought: string;
  steps: StreamingStep[];
  routingInfo: RoutingInfo | null;
  sources: Source[];  // NEW: Sources en temps réel
  error: string | null;
  retryCount: number; // NEW: Compteur de retry
  isReconnecting: boolean; // NEW: Indicateur de reconnexion
}

interface UseStreamingChatOptions {
  apiUrl?: string;
  onComplete?: (message: Message) => void;
  onError?: (error: Error) => void;
  timeout?: number; // NEW: Timeout en ms (default: 60000)
  maxRetries?: number; // NEW: Nombre max de retries (default: 3)
}

interface SendStreamOptions {
  useWebSearch?: boolean;
  forceRag?: boolean;
  enableReflection?: boolean;
  sessionId?: string;
}

// ===== Constants =====

const DEFAULT_TIMEOUT = 60000; // 60 secondes
const DEFAULT_MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 seconde

// ===== Helpers =====

const generateId = () => Math.random().toString(36).substring(2, 15);

const getApiKey = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("rag_api_key");
};

/**
 * Calcule le délai de retry avec backoff exponentiel
 */
const getRetryDelay = (retryCount: number): number => {
  return Math.min(INITIAL_RETRY_DELAY * Math.pow(2, retryCount), 10000);
};

/**
 * Vérifie si l'erreur est récupérable (retry possible)
 */
const isRetryableError = (error: Error): boolean => {
  const message = error.message.toLowerCase();
  // Retry sur erreurs réseau ou timeout, pas sur erreurs auth
  return (
    message.includes("network") ||
    message.includes("fetch") ||
    message.includes("timeout") ||
    message.includes("503") ||
    message.includes("502")
  );
};

// ===== Hook =====

export function useStreamingChat(options?: UseStreamingChatOptions) {
  const apiUrl = options?.apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const timeout = options?.timeout || DEFAULT_TIMEOUT;
  const maxRetries = options?.maxRetries || DEFAULT_MAX_RETRIES;
  
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    currentContent: "",
    currentThought: "",
    steps: [],
    routingInfo: null,
    sources: [],
    error: null,
    retryCount: 0,
    isReconnecting: false,
  });

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastRequestRef = useRef<{ question: string; options?: SendStreamOptions } | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  /**
   * Initialise les étapes de progression
   */
  const initializeSteps = useCallback((enableReflection: boolean) => {
    const steps: StreamingStep[] = [
      { type: "routing", status: "pending", label: "Analyse de la requête" },
      { type: "search_rag", status: "pending", label: "Recherche dans vos documents" },
      { type: "search_web", status: "pending", label: "Consultation du web" },
      { type: "generating", status: "pending", label: enableReflection ? "Réflexion approfondie" : "Génération de la réponse" },
    ];
    return steps;
  }, []);

  /**
   * Met à jour une étape spécifique
   */
  const updateStep = useCallback((
    type: StreamingStep["type"],
    status: StreamingStep["status"],
    details?: string
  ) => {
    setState(prev => ({
      ...prev,
      steps: prev.steps.map(step =>
        step.type === type ? { ...step, status, details } : step
      ),
    }));
  }, []);

  /**
   * Ajoute une source en temps réel
   */
  const addSource = useCallback((source: Source) => {
    setState(prev => ({
      ...prev,
      sources: [...prev.sources, source],
    }));
  }, []);

  /**
   * Clear le timeout
   */
  const clearTimeoutRef = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  /**
   * Envoie une requête en streaming avec gestion du timeout et retry
   */
  const sendStreamInternal = useCallback(async (
    question: string,
    sendOptions?: SendStreamOptions,
    isRetry: boolean = false
  ): Promise<Message | null> => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return null;

    // Vérifier la clé API
    const apiKey = getApiKey();
    if (!apiKey) {
      toast.error("Clé API manquante", {
        description: "Configurez votre clé API dans les paramètres",
      });
      return null;
    }

    // Sauvegarder la requête pour retry
    lastRequestRef.current = { question: trimmedQuestion, options: sendOptions };

    // Reset ou update state selon retry
    if (!isRetry) {
      setState({
        isStreaming: true,
        currentContent: "",
        currentThought: "",
        steps: initializeSteps(sendOptions?.enableReflection || false),
        routingInfo: null,
        sources: [],
        error: null,
        retryCount: 0,
        isReconnecting: false,
      });
    } else {
      setState(prev => ({
        ...prev,
        isReconnecting: true,
        error: null,
      }));
    }

    // Créer AbortController
    abortControllerRef.current = new AbortController();

    // Setup timeout
    clearTimeoutRef();
    timeoutRef.current = setTimeout(() => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        setState(prev => ({
          ...prev,
          error: `Timeout après ${timeout / 1000} secondes`,
          isStreaming: false,
        }));
        toast.error("Timeout", { 
          description: "La réponse prend trop de temps. Réessayez." 
        });
      }
    }, timeout);

    try {
      // POST request avec fetch pour le streaming
      const response = await fetch(`${apiUrl}/query/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          session_id: sendOptions?.sessionId,
          use_web_search: sendOptions?.useWebSearch,
          use_rag: sendOptions?.forceRag,
          enable_reflection: sendOptions?.enableReflection,
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      });

      // Clear timeout - on a reçu une réponse
      clearTimeoutRef();

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      // Reset isReconnecting
      if (isRetry) {
        setState(prev => ({ ...prev, isReconnecting: false }));
        toast.success("Reconnecté !");
      }

      // Lire le stream SSE
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let fullContent = "";
      let fullThought = "";
      let sources: Source[] = [];
      let conversationId: string | null = null;
      let routingInfo: RoutingInfo | null = null;
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Parser les événements SSE
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Garder la dernière ligne incomplète

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            // On ignore le type pour l'instant, on parse les data
            continue;
          }
          
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              
              // Routing events
              if (data.status === "started" && !data.intent) {
                updateStep("routing", "in_progress");
              } 
              else if (data.intent) {
                updateStep("routing", "completed");
                routingInfo = {
                  intent: data.intent,
                  use_rag: data.use_rag,
                  use_web: data.use_web,
                  confidence: data.confidence || 0.8,
                  reasoning: data.reasoning || "",
                  latency_ms: data.latency_ms || 0,
                };
                setState(prev => ({ ...prev, routingInfo }));
                
                if (!data.use_rag) {
                  updateStep("search_rag", "completed", "Non requis");
                }
                if (!data.use_web) {
                  updateStep("search_web", "completed", "Non requis");
                }
              }
              // Search events
              else if (data.type === "rag") {
                if (data.results !== undefined) {
                  updateStep("search_rag", "completed", `${data.results} documents`);
                } else {
                  updateStep("search_rag", "in_progress");
                }
              }
              else if (data.type === "web") {
                if (data.found !== undefined) {
                  updateStep("search_web", "completed", data.found ? "Résultats trouvés" : "Aucun résultat");
                } else {
                  updateStep("search_web", "in_progress");
                }
              }
              // Content chunks
              else if (data.content !== undefined && !data.is_thought) {
                updateStep("generating", "in_progress");
                fullContent += data.content;
                setState(prev => ({ ...prev, currentContent: fullContent }));
              }
              // Thought chunks
              else if (data.content !== undefined && data.is_thought) {
                fullThought += data.content;
                setState(prev => ({ ...prev, currentThought: fullThought }));
              }
              // Source event (NEW - temps réel)
              else if (data.source_type) {
                const source: Source = {
                  source_type: data.source_type,
                  content_preview: data.content_preview,
                  similarity_score: data.similarity_score,
                  url: data.url,
                  document_id: data.document_id,
                };
                sources.push(source);
                addSource(source);
              }
              // Complete event
              else if (data.conversation_id !== undefined) {
                updateStep("generating", "completed");
                conversationId = data.conversation_id;
                if (data.sources && data.sources.length > 0) {
                  sources = data.sources;
                  setState(prev => ({ ...prev, sources: data.sources }));
                }
              }
              // Error event
              else if (data.error) {
                throw new Error(data.error);
              }
            } catch (parseError) {
              // Ignorer les erreurs de parsing pour les lignes incomplètes
              console.debug("SSE parse error:", parseError);
            }
          }
        }
      }

      // Créer le message final
      const message: Message = {
        id: generateId(),
        role: "assistant",
        content: fullContent,
        timestamp: new Date(),
        sources,
        conversationId: conversationId || undefined,
        thoughtProcess: fullThought || undefined,
        routingInfo: routingInfo || undefined,
      };

      setState(prev => ({
        ...prev,
        isStreaming: false,
        retryCount: 0,
      }));

      options?.onComplete?.(message);
      return message;

    } catch (error) {
      clearTimeoutRef();
      const err = error instanceof Error ? error : new Error(String(error));
      
      // Gérer l'annulation
      if (err.name === "AbortError") {
        setState(prev => ({
          ...prev,
          isStreaming: false,
          isReconnecting: false,
          error: null,
        }));
        return null;
      }

      // Check if we should retry
      const currentRetryCount = state.retryCount;
      if (isRetryableError(err) && currentRetryCount < maxRetries) {
        const delay = getRetryDelay(currentRetryCount);
        
        setState(prev => ({
          ...prev,
          retryCount: prev.retryCount + 1,
          isReconnecting: true,
          error: `Nouvelle tentative dans ${delay / 1000}s...`,
        }));

        toast.warning("Connexion perdue", {
          description: `Tentative de reconnexion ${currentRetryCount + 1}/${maxRetries}...`,
        });

        // Retry après délai
        await new Promise(resolve => setTimeout(resolve, delay));
        return sendStreamInternal(question, sendOptions, true);
      }

      // Déterminer le message d'erreur final
      let errorMessage = err.message;
      if (err.message.includes("401")) {
        errorMessage = "Clé API invalide ou expirée";
      } else if (err.message.includes("429")) {
        errorMessage = "Trop de requêtes. Réessayez dans quelques instants.";
      } else if (err.message.includes("Network") || err.message.includes("fetch")) {
        errorMessage = "Impossible de contacter le serveur";
      }

      setState(prev => ({
        ...prev,
        isStreaming: false,
        isReconnecting: false,
        error: errorMessage,
      }));

      toast.error("Erreur de streaming", { description: errorMessage });
      options?.onError?.(err);
      return null;
    }
  }, [apiUrl, timeout, maxRetries, initializeSteps, updateStep, addSource, clearTimeoutRef, state.retryCount, options]);

  /**
   * Wrapper public pour sendStream
   */
  const sendStream = useCallback(async (
    question: string,
    sendOptions?: SendStreamOptions
  ): Promise<Message | null> => {
    return sendStreamInternal(question, sendOptions, false);
  }, [sendStreamInternal]);

  /**
   * Retry manuellement la dernière requête
   */
  const retry = useCallback(async (): Promise<Message | null> => {
    if (!lastRequestRef.current) {
      toast.error("Aucune requête à réessayer");
      return null;
    }
    
    const { question, options: sendOptions } = lastRequestRef.current;
    setState(prev => ({ ...prev, retryCount: 0 })); // Reset retry count
    return sendStreamInternal(question, sendOptions, true);
  }, [sendStreamInternal]);

  /**
   * Annule le streaming en cours
   */
  const cancelStream = useCallback(() => {
    clearTimeoutRef();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState(prev => ({
      ...prev,
      isStreaming: false,
      isReconnecting: false,
    }));
    toast.info("Streaming annulé");
  }, [clearTimeoutRef]);

  /**
   * Reset l'état
   */
  const reset = useCallback(() => {
    clearTimeoutRef();
    setState({
      isStreaming: false,
      currentContent: "",
      currentThought: "",
      steps: [],
      routingInfo: null,
      sources: [],
      error: null,
      retryCount: 0,
      isReconnecting: false,
    });
    lastRequestRef.current = null;
  }, [clearTimeoutRef]);

  return {
    // State
    isStreaming: state.isStreaming,
    currentContent: state.currentContent,
    currentThought: state.currentThought,
    steps: state.steps,
    routingInfo: state.routingInfo,
    sources: state.sources, // NEW
    error: state.error,
    retryCount: state.retryCount, // NEW
    isReconnecting: state.isReconnecting, // NEW

    // Actions
    sendStream,
    cancelStream,
    reset,
    retry, // NEW
  };
}

export default useStreamingChat;
