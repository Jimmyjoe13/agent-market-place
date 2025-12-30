/**
 * Playground Page (Refactored)
 * ============================
 * 
 * Interface avancée pour tester l'API RAG avec contrôle total des paramètres.
 * Version améliorée avec panneaux escamotables et persistance localStorage.
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
  Code2,
  PanelRightOpen,
  PanelRightClose
} from "lucide-react";
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
import { usePanelState } from "@/hooks/usePanelState";
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
  
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Panel state management with persistence
  const {
    leftCollapsed,
    rightCollapsed,
    codePreviewCollapsed,
    toggleLeft,
    toggleRight,
    toggleCodePreview,
    isHydrated,
  } = usePanelState();

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
      {/* Parameters Panel (Left) - Collapsible */}
      <PlaygroundParameters 
        parameters={parameters} 
        setParameters={setParameters}
        onReset={() => setParameters(DEFAULT_PARAMS)}
        isCollapsed={leftCollapsed}
        onToggleCollapse={toggleLeft}
      />

      {/* Main Playground Area (Middle) */}
      <div className="flex-1 flex flex-col min-w-0 bg-background">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Terminal className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-foreground uppercase tracking-widest">Playground</h1>
              <p className="text-[10px] text-muted-foreground font-medium">TEST L'API EN CONDITIONS RÉELLES</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {!hasApiKey && (
              <Badge variant="outline" className="border-warning/30 bg-warning/5 text-warning text-[10px]">
                API KEY REQUISE
              </Badge>
            )}
            
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 text-xs gap-2 text-muted-foreground hover:text-destructive"
                    onClick={newConversation}
                  >
                    <Eraser className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline">Clear</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Effacer la conversation</TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-primary lg:hidden"
                    onClick={toggleRight}
                  >
                    {rightCollapsed ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {rightCollapsed ? "Ouvrir configuration" : "Fermer configuration"}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6" ref={scrollContainerRef}>
          <div className="max-w-4xl mx-auto space-y-8 pb-12">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center pt-20 text-center space-y-4">
                <div className="h-12 w-12 rounded-2xl bg-primary/5 flex items-center justify-center animate-subtle-pulse">
                  <Bot className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-sm font-medium text-foreground">Prêt à tester l'API ?</h3>
                  <p className="text-xs text-muted-foreground">Saisissez un message ci-dessous pour commencer la simulation.</p>
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
                    message.role === "user" ? "bg-secondary" : "bg-primary/20"
                  )}>
                    {message.role === "user" ? (
                      <User className="h-4 w-4 text-secondary-foreground" />
                    ) : (
                      <Bot className="h-4 w-4 text-primary" />
                    )}
                  </div>
                  <div className={cn(
                    "flex-1 max-w-[85%] space-y-1",
                    message.role === "user" ? "text-right" : "text-left"
                  )}>
                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                      {message.role === "user" ? "Client Request" : "API Response"}
                    </div>
                    {message.isLoading ? (
                      <div className="space-y-2">
                        <Skeleton className="h-4 w-full bg-primary/5" />
                        <Skeleton className="h-4 w-[60%] bg-primary/5" />
                      </div>
                    ) : (
                      <div className={cn(
                        "p-3 rounded-xl text-sm leading-relaxed",
                        message.role === "user" 
                          ? "bg-secondary border border-border text-secondary-foreground" 
                          : "bg-primary/5 text-foreground"
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
        <div className="p-6 border-t border-border shadow-[0_-20px_50px_rgba(0,0,0,0.3)]">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="relative group">
              <Textarea 
                placeholder="Entrez votre question..."
                className="bg-secondary/50 border-border min-h-[100px] pr-14 custom-scrollbar focus-visible:ring-primary/50 transition-all text-sm"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
              />
              <Button 
                size="icon"
                type="submit"
                disabled={!input.trim() || isLoading}
                className="absolute bottom-3 right-3 bg-primary hover:bg-primary/90 h-9 w-9 shadow-lg glow-brand"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
            <div className="mt-3 flex items-center justify-between">
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground font-mono">
                <span className="flex items-center gap-1">
                  <kbd className="px-1 bg-secondary border border-border rounded">Enter</kbd> to send
                </span>
                <span className="flex items-center gap-1 hidden sm:flex">
                  <kbd className="px-1 bg-secondary border border-border rounded">Shift+Enter</kbd> for newline
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px] text-success font-mono border-success/20">
                  STREAMING ENABLED
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Code Preview (Bottom) - Collapsible */}
        <CodePreview 
          parameters={parameters}
          requestContent={input}
        />
      </div>

      {/* Agent Config Panel (Right) - Collapsible on desktop, hidden on mobile unless toggled */}
      <div 
        className={cn(
          "border-l border-border bg-card/50 overflow-y-auto transition-all duration-300 ease-in-out",
          // Desktop: toujours visible, width change based on collapsed state
          "hidden lg:block",
          rightCollapsed ? "lg:w-0 lg:border-l-0" : "lg:w-80",
          // Mobile: absolute overlay when toggled open
          !rightCollapsed && "fixed inset-y-0 right-0 w-80 z-50 lg:relative lg:inset-auto"
        )}
      >
        {!rightCollapsed && (
          <div className="p-4">
            <div className="flex items-center justify-between mb-4 lg:hidden">
              <h2 className="font-semibold text-sm">Configuration Agent</h2>
              <Button variant="ghost" size="icon" onClick={toggleRight}>
                <PanelRightClose className="h-4 w-4" />
              </Button>
            </div>
            <AgentConfigPanel />
          </div>
        )}
      </div>
      
      {/* Backdrop for mobile right panel */}
      {!rightCollapsed && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={toggleRight}
        />
      )}
    </div>
  );
}
