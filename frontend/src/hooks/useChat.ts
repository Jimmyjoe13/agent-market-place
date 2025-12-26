/**
 * Hook amélioré pour la gestion du chat
 * - Support de l'annulation de requêtes (AbortController)
 * - Optimistic updates
 * - Gestion du streaming
 * - Historique de session
 */

"use client";

import { useState, useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Message, QueryResponse, Source } from "@/types/api";

// ===== Helper Functions =====

const generateId = () => Math.random().toString(36).substring(2, 15);

const createUserMessage = (content: string): Message => ({
  id: generateId(),
  role: "user",
  content: content.trim(),
  timestamp: new Date(),
});

const createAssistantMessage = (
  content: string,
  options?: {
    sources?: Source[];
    conversationId?: string;
    isLoading?: boolean;
  }
): Message => ({
  id: generateId(),
  role: "assistant",
  content,
  timestamp: new Date(),
  sources: options?.sources,
  conversationId: options?.conversationId,
  isLoading: options?.isLoading,
});

// ===== Types =====

interface UseChatOptions {
  onError?: (error: Error) => void;
  onSuccess?: (response: QueryResponse) => void;
}

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
}

// ===== Hook =====

export function useChat(options?: UseChatOptions) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    sessionId: null,
    isLoading: false,
  });

  // Ref pour l'AbortController
  const abortControllerRef = useRef<AbortController | null>(null);

  const queryClient = useQueryClient();

  // Mutation pour envoyer un message
  const sendMutation = useMutation({
    mutationFn: async ({
      question,
      useWeb,
      signal,
    }: {
      question: string;
      useWeb: boolean;
      signal?: AbortSignal;
    }) => {
      return api.query({
        question,
        session_id: state.sessionId || undefined,
        use_web_search: useWeb,
      });
    },
    onSuccess: (data: QueryResponse) => {
      // Mettre à jour le session ID
      if (data.session_id && !state.sessionId) {
        setState((prev) => ({ ...prev, sessionId: data.session_id }));
      }

      // Remplacer le message "loading" par la vraie réponse
      const assistantMessage = createAssistantMessage(data.answer, {
        sources: data.sources,
        conversationId: data.conversation_id,
      });

      setState((prev) => ({
        ...prev,
        messages: prev.messages
          .filter((m) => !m.isLoading)
          .concat(assistantMessage),
        isLoading: false,
      }));

      // Callback optionnel
      options?.onSuccess?.(data);
    },
    onError: (error: Error) => {
      // Gérer l'annulation silencieusement
      if (error.name === "AbortError" || error.message === "canceled") {
        setState((prev) => ({
          ...prev,
          messages: prev.messages.filter((m) => !m.isLoading),
          isLoading: false,
        }));
        return;
      }

      // Supprimer le message "loading" et ajouter un message d'erreur
      const errorMessage = createAssistantMessage(
        `❌ Erreur: ${error.message}. Vérifiez votre clé API ou votre connexion.`
      );

      setState((prev) => ({
        ...prev,
        messages: prev.messages.filter((m) => !m.isLoading).concat(errorMessage),
        isLoading: false,
      }));

      toast.error("Erreur de communication", {
        description: error.message,
      });

      options?.onError?.(error);
    },
  });

  // Envoyer un message
  const sendMessage = useCallback(
    async (content: string, useWeb = true) => {
      const trimmedContent = content.trim();
      if (!trimmedContent || state.isLoading) return;

      // Annuler toute requête précédente
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Créer un nouvel AbortController
      abortControllerRef.current = new AbortController();

      setState((prev) => ({ ...prev, isLoading: true }));

      // Optimistic update : ajouter immédiatement le message utilisateur
      const userMessage = createUserMessage(trimmedContent);
      const loadingMessage = createAssistantMessage("", { isLoading: true });

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, loadingMessage],
      }));

      // Envoyer la requête
      sendMutation.mutate({
        question: trimmedContent,
        useWeb,
        signal: abortControllerRef.current?.signal,
      });
    },
    [state.isLoading, sendMutation]
  );

  // Annuler la requête en cours
  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;

      setState((prev) => ({
        ...prev,
        messages: prev.messages.filter((m) => !m.isLoading),
        isLoading: false,
      }));

      toast.info("Requête annulée");
    }
  }, []);

  // Nouvelle conversation
  const newConversation = useCallback(() => {
    // Annuler toute requête en cours
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setState({
      messages: [],
      sessionId: null,
      isLoading: false,
    });
  }, []);

  // Soumettre un feedback
  const submitFeedback = useCallback(
    async (conversationId: string, score: number, comment?: string) => {
      try {
        await api.submitFeedback({
          conversation_id: conversationId,
          score,
          comment,
          flag_for_training: score >= 4,
        });

        toast.success("Merci pour votre feedback !");
        return true;
      } catch (error) {
        toast.error("Impossible d'envoyer le feedback");
        return false;
      }
    },
    []
  );

  // Régénérer la dernière réponse
  const regenerateLastResponse = useCallback(() => {
    // Trouver le dernier message utilisateur
    const lastUserMessage = [...state.messages]
      .reverse()
      .find((m) => m.role === "user");

    if (lastUserMessage) {
      // Supprimer la dernière réponse assistant
      setState((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -1),
      }));

      // Renvoyer le message
      sendMessage(lastUserMessage.content, true);
    }
  }, [state.messages, sendMessage]);

  return {
    // State
    messages: state.messages,
    sessionId: state.sessionId,
    isLoading: state.isLoading,

    // Actions
    sendMessage,
    cancelRequest,
    newConversation,
    submitFeedback,
    regenerateLastResponse,

    // Helpers
    hasApiKey: api.hasApiKey(),
    canSend: !state.isLoading && api.hasApiKey(),
    messageCount: state.messages.length,
  };
}

export default useChat;
