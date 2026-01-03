"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { MessageCircle, X, Send, Bot, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ==================== Types ====================

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatResponse {
  response: string;
  suggestions: string[];
}

// ==================== Configuration ====================

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const DEFAULT_SUGGESTIONS = [
  "Comment créer une clé API ?",
  "Comment ajouter un document ?",
  "Quels sont les tarifs ?",
  "Contact support",
];

const MAX_HISTORY = 10;

// ==================== Component ====================

export function HelpWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Bonjour ! Je suis l'assistant d'aide de RAG Agentia. Comment puis-je vous aider ?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when opening
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Build history for API (last N messages)
  const buildHistory = useCallback((): Array<{ role: "user" | "assistant"; content: string }> => {
    return messages
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role, content: m.content }));
  }, [messages]);

  // Send message to backend
  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: messageText.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/help/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageText.trim(),
          history: buildHistory(),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: ChatResponse = await response.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      if (data.suggestions?.length > 0) {
        setSuggestions(data.suggestions);
      }
    } catch (error) {
      console.error("Help chat error:", error);
      
      const errorMessage: Message = {
        role: "assistant",
        content: "Désolé, je rencontre un problème technique. Réessayez dans quelques instants ou contactez support@rag-agentia.com.",
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  // Format message content (basic markdown support)
  const formatContent = (content: string) => {
    return content
      .split("\n")
      .map((line, i) => (
        <span key={i}>
          {line.startsWith("- ") ? (
            <span className="block pl-4">• {line.slice(2)}</span>
          ) : (
            line
          )}
          {i < content.split("\n").length - 1 && <br />}
        </span>
      ));
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center",
          "rounded-full bg-gradient-to-br from-indigo-500 to-purple-600",
          "text-white shadow-lg transition-all duration-300",
          "hover:scale-110 hover:shadow-xl",
          "focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2",
          isOpen && "scale-0 opacity-0"
        )}
        aria-label="Ouvrir l'aide"
      >
        <MessageCircle className="h-6 w-6" />
        {/* Pulse animation */}
        <span className="absolute h-full w-full animate-ping rounded-full bg-indigo-400 opacity-20" />
      </button>

      {/* Chat Window */}
      <div
        className={cn(
          "fixed bottom-6 right-6 z-50 flex flex-col overflow-hidden",
          "w-[400px] max-w-[calc(100vw-48px)] rounded-2xl",
          "border border-border/50 bg-background/95 backdrop-blur-xl",
          "shadow-2xl transition-all duration-300",
          isOpen
            ? "h-[550px] opacity-100 translate-y-0"
            : "h-0 opacity-0 translate-y-4 pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">Aide & FAQ</h3>
              <p className="text-xs text-white/70">Réponse instantanée</p>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="rounded-full p-2 hover:bg-white/20 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-3 text-sm animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
                message.role === "user"
                  ? "ml-auto bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-br-sm"
                  : "bg-muted/80 rounded-bl-sm"
              )}
            >
              <div className="whitespace-pre-wrap leading-relaxed">
                {formatContent(message.content)}
              </div>
              <div
                className={cn(
                  "text-[10px] mt-1.5 opacity-60",
                  message.role === "user" ? "text-right" : ""
                )}
              >
                {message.timestamp.toLocaleTimeString("fr-FR", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>
          ))}
          
          {/* Typing indicator */}
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground animate-in fade-in-0">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Réponse en cours...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestions */}
        {messages.length <= 2 && !isLoading && (
          <div className="px-4 pb-2">
            <p className="text-xs text-muted-foreground mb-2">Suggestions :</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.slice(0, 4).map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-muted transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="border-t border-border/50 p-4">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question..."
              disabled={isLoading}
              className={cn(
                "flex-1 rounded-full border border-border bg-background px-4 py-2.5 text-sm",
                "focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "placeholder:text-muted-foreground"
              )}
            />
            <Button
              type="submit"
              size="icon"
              disabled={isLoading || !input.trim()}
              className={cn(
                "h-10 w-10 rounded-full shrink-0",
                "bg-gradient-to-br from-indigo-500 to-purple-600",
                "hover:opacity-90 disabled:opacity-50"
              )}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

export default HelpWidget;
