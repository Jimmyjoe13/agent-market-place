/**
 * Playground Page
 * ===============
 * 
 * Interface avancée pour tester l'API RAG avec contrôle total des paramètres.
 * Reutilise les composants et la logique de chat.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { 
  Send, 
  Loader2, 
  Bot, 
  User, 
  Terminal,
  Eraser,
  Settings2,
  Code2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { PlaygroundParameters } from "@/components/playground/parameters";
import { CodePreview } from "@/components/playground/code-preview";
import AgentConfigPanel from "@/components/playground/AgentConfigPanel";
import type { Message } from "@/types/api";

// Default parameters
const DEFAULT_PARAMS = {
  model: "mistral-small",
  temperature: 0.7,
  maxTokens: 2048,
  topP: 1,
  systemPrompt: "Vous êtes un assistant IA expert en RAG (Retrieval Augmented Generation). Répondez de manière précise et concise en vous basant sur le contexte fourni.",
  useWebSearch: true
};

export default function PlaygroundPage() {
  const [input, setInput] = useState("");
  const [parameters, setParameters] = useState(DEFAULT_PARAMS);
  const [showCode, setShowCode] = useState(true);
  
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { 
    messages, 
    isLoading, 
    sendMessage, 
    newConversation,
    hasApiKey 
  } = useChat();

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      // Pour le moment on passe system_prompt, d'autres params suivront si supportés au backend
      sendMessage(input, parameters.useWebSearch); 
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Parameters Panel (Left) */}
      <PlaygroundParameters 
        parameters={parameters} 
        setParameters={setParameters}
        onReset={() => setParameters(DEFAULT_PARAMS)}
      />

      {/* Main Playground Area (Middle) */}
      <div className="flex-1 flex flex-col min-w-0 bg-zinc-950">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-white/5 px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
              <Terminal className="h-4 w-4 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-zinc-100 uppercase tracking-widest">Playground</h1>
              <p className="text-[10px] text-zinc-500 font-medium">TEST L'API EN CONDITIONS RÉELLES</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {!hasApiKey && (
              <Badge variant="outline" className="border-amber-500/30 bg-amber-500/5 text-amber-500 text-[10px]">
                API KEY REQUISE
              </Badge>
            )}
            <Button 
                variant="ghost" 
                size="sm" 
                className="h-8 text-xs gap-2 text-zinc-400 hover:text-red-400"
                onClick={newConversation}
            >
              <Eraser className="h-3.5 w-3.5" />
              Clear Chat
            </Button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6" ref={scrollContainerRef}>
          <div className="max-w-4xl mx-auto space-y-8 pb-12">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center pt-20 text-center space-y-4">
                <div className="h-12 w-12 rounded-2xl bg-white/5 flex items-center justify-center animate-pulse">
                  <Bot className="h-6 w-6 text-zinc-500" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-sm font-medium text-zinc-300">Prêt à tester l'API ?</h3>
                  <p className="text-xs text-zinc-500">Saisissez un message ci-dessous pour commencer la simulation.</p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div 
                  key={message.id}
                  className={cn(
                    "flex gap-4 group",
                    message.role === "user" ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <div className={cn(
                    "shrink-0 h-8 w-8 rounded-lg flex items-center justify-center",
                    message.role === "user" ? "bg-zinc-800" : "bg-indigo-600/20"
                  )}>
                    {message.role === "user" ? (
                      <User className="h-4 w-4 text-zinc-400" />
                    ) : (
                      <Bot className="h-4 w-4 text-indigo-400" />
                    )}
                  </div>
                  <div className={cn(
                    "flex-1 max-w-[85%] space-y-1",
                    message.role === "user" ? "text-right" : "text-left"
                  )}>
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-tight">
                      {message.role === "user" ? "Client Request" : "API Response"}
                    </div>
                    {message.isLoading ? (
                      <div className="space-y-2">
                        <Skeleton className="h-4 w-full bg-white/5" />
                        <Skeleton className="h-4 w-[60%] bg-white/5" />
                      </div>
                    ) : (
                      <div className={cn(
                        "p-3 rounded-xl text-sm leading-relaxed",
                        message.role === "user" 
                          ? "bg-zinc-900 border border-white/5 text-zinc-300" 
                          : "bg-white/5 text-zinc-200"
                      )}>
                        {message.content}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-white/5 shadow-[0_-20px_50px_rgba(0,0,0,0.5)]">
            <div className="max-w-4xl mx-auto">
                <form onSubmit={handleSubmit} className="relative group">
                    <Textarea 
                        placeholder="Entrez votre question..."
                        className="bg-zinc-900/50 border-white/10 min-h-[100px] pr-14 custom-scrollbar focus-visible:ring-indigo-500/50 transition-all text-sm"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                    />
                    <Button 
                        size="icon"
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="absolute bottom-3 right-3 bg-indigo-600 hover:bg-indigo-700 h-9 w-9 shadow-lg shadow-indigo-600/20"
                    >
                        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                </form>
                <div className="mt-3 flex items-center justify-between">
                    <div className="flex items-center gap-4 text-[10px] text-zinc-500 font-mono">
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 bg-zinc-900 border border-white/10 rounded">Enter</kbd> to send
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="px-1 bg-zinc-900 border border-white/10 rounded">Shift+Enter</kbd> for newline
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px] text-emerald-500 font-mono border-emerald-500/20">STREAMING ENABLED</Badge>
                    </div>
                </div>
            </div>
        </div>

        {/* Code Preview (Bottom) */}
        <CodePreview 
            parameters={parameters}
            requestContent={input}
        />
      </div>

      {/* Agent Config Panel (Right) */}
      <div className="hidden lg:block w-80 border-l border-white/5 bg-zinc-950/50 overflow-y-auto">
        <div className="p-4">
          <AgentConfigPanel />
        </div>
      </div>
    </div>
  );
}
