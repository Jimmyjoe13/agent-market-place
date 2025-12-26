/**
 * Page de chat avec l'agent RAG
 * Utilise le store Zustand pour les préférences
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Globe, Loader2, ThumbsUp, ThumbsDown, Bot, User, StopCircle, RefreshCw, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { usePreferencesStore } from "@/stores";
import type { Message, Source } from "@/types/api";

// Composant pour afficher les sources
function SourceBadges({ sources }: { sources?: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {sources.map((source, idx) => (
        <Badge
          key={idx}
          variant="outline"
          className={cn(
            "text-xs",
            source.source_type === "perplexity"
              ? "border-violet-500/30 bg-violet-500/10 text-violet-400"
              : "border-indigo-500/30 bg-indigo-500/10 text-indigo-400"
          )}
        >
          {source.source_type === "perplexity" ? "🌐 Web" : "📄 Document"}
          {source.similarity_score && ` (${(source.similarity_score * 100).toFixed(0)}%)`}
        </Badge>
      ))}
    </div>
  );
}

// Composant pour un message
function ChatMessage({
  message,
  onFeedback,
}: {
  message: Message;
  onFeedback?: (score: number) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-4 px-4 py-6 sm:px-6",
        isUser ? "bg-transparent" : "bg-zinc-900/30"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-indigo-600"
            : "bg-gradient-to-br from-violet-600 to-indigo-600"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="font-medium">
            {isUser ? "Vous" : "Assistant"}
          </span>
          <span className="text-xs text-zinc-500">
            {message.timestamp.toLocaleTimeString("fr-FR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {message.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/4 bg-zinc-800" />
            <Skeleton className="h-4 w-1/2 bg-zinc-800" />
          </div>
        ) : (
          <>
            <div className="prose prose-invert prose-sm max-w-none break-words">
              <p className="whitespace-pre-wrap leading-relaxed text-zinc-200">
                {message.content}
              </p>
            </div>
            <SourceBadges sources={message.sources} />
          </>
        )}

        {/* Feedback buttons - only for assistant messages */}
        {!isUser && !message.isLoading && onFeedback && (
          <div className="flex items-center gap-2 pt-2">
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onFeedback(5)}
                    className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-green-400"
                  >
                    <ThumbsUp className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Bonne réponse</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onFeedback(1)}
                    className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"
                  >
                    <ThumbsDown className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Mauvaise réponse</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>
    </div>
  );
}

// Page principale
export default function ChatPage() {
  const [input, setInput] = useState("");
  const [showScrollButton, setShowScrollButton] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Préférences depuis le store Zustand
  const useWebSearch = usePreferencesStore((state) => state.useWebSearch);
  const setUseWebSearch = usePreferencesStore((state) => state.setUseWebSearch);

  const { 
    messages, 
    isLoading, 
    sendMessage, 
    submitFeedback, 
    hasApiKey,
    cancelRequest,
    regenerateLastResponse,
  } = useChat();

  // Scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle scroll to show/hide scroll button
  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollButton(!isNearBottom && messages.length > 0);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      sendMessage(input, useWebSearch);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFeedback = async (conversationId: string, score: number) => {
    await submitFeedback(conversationId, score);
  };

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-zinc-800 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">Chat</h1>
          <p className="text-sm text-zinc-500">
            Discutez avec votre assistant personnel
          </p>
        </div>
        {!hasApiKey && (
          <Badge variant="outline" className="border-amber-500/50 text-amber-400">
            Clé API non configurée
          </Badge>
        )}
      </div>

      {/* Messages - Zone scrollable */}
      <div 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20">
              <Bot className="h-8 w-8 text-indigo-400" />
            </div>
            <h2 className="mb-2 text-xl font-semibold">
              Bienvenue !
            </h2>
            <p className="max-w-md text-zinc-400">
              Je suis votre copilote IA. Posez-moi une question et je
              chercherai dans vos documents et sur le web pour vous répondre.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onFeedback={
                  message.conversationId
                    ? (score) => handleFeedback(message.conversationId!, score)
                    : undefined
                }
              />
            ))}
            {/* Invisible element to scroll to */}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <div className="absolute bottom-32 left-1/2 z-10 -translate-x-1/2">
          <Button
            size="sm"
            variant="secondary"
            onClick={scrollToBottom}
            className="gap-2 rounded-full bg-zinc-800 shadow-lg hover:bg-zinc-700"
          >
            <ChevronDown className="h-4 w-4" />
            Voir la suite
          </Button>
        </div>
      )}

      {/* Input - Zone fixe */}
      <div className="shrink-0 border-t border-zinc-800 bg-zinc-950 p-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Posez votre question..."
              className="min-h-[80px] resize-none bg-zinc-900 pr-12 text-zinc-100 placeholder:text-zinc-500"
              disabled={isLoading}
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || isLoading}
              className="absolute bottom-2 right-2 h-8 w-8 bg-indigo-600 hover:bg-indigo-500"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Options */}
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={useWebSearch}
                onChange={(e) => setUseWebSearch(e.target.checked)}
                className="h-4 w-4 rounded border-zinc-700 bg-zinc-800 text-indigo-600"
              />
              <Globe className="h-4 w-4" />
              Recherche web
            </label>

            {/* Bouton Annuler si chargement */}
            {isLoading && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={cancelRequest}
                className="gap-2 text-red-400 hover:text-red-300"
              >
                <StopCircle className="h-4 w-4" />
                Annuler
              </Button>
            )}

            {/* Bouton Régénérer si messages et pas en cours */}
            {messages.length > 0 && !isLoading && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={regenerateLastResponse}
                className="gap-2 text-zinc-400 hover:text-zinc-300"
              >
                <RefreshCw className="h-4 w-4" />
                Régénérer
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
