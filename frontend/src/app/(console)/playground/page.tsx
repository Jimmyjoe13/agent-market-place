/**
 * Playground Page (Refactored)
 * ============================
 * 
 * Interface avancée pour tester l'API RAG avec contrôle total des paramètres.
 * Version améliorée avec panneaux escamotables et persistance localStorage.
 */

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
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
  PanelRightClose,
  Sparkles,
  Zap,
  ShieldCheck,
  Globe,
  Key,
  Plus
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { usePanelState } from "@/hooks/usePanelState";
import { useUserApiKeysManager } from "@/hooks/useUserApiKeys";
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
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Hook Clés API (Architecture v3: 1 Clé = 1 Agent = 1 RAG)
  const { keys, isLoading: isLoadingKeys } = useUserApiKeysManager();

  // Clé sélectionnée
  const selectedKey = keys.find(k => k.id === selectedKeyId) || keys[0];

  // Auto-select first key if none selected
  useEffect(() => {
    if (keys.length > 0 && !selectedKeyId) {
        const savedId = localStorage.getItem('playground_key_id');
        const found = savedId ? keys.find(k => k.id === savedId) : null;
        if (found) {
            setSelectedKeyId(found.id);
        } else {
            setSelectedKeyId(keys[0].id);
        }
    }
  }, [keys, selectedKeyId]);

  // Persist selection
  useEffect(() => {
    if (selectedKeyId) {
        localStorage.setItem('playground_key_id', selectedKeyId);
    }
  }, [selectedKeyId]);


  // Panel state management with persistence
  const {
    rightCollapsed,
    codePreviewCollapsed,
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

  const handleConfigChange = useCallback((newParams: any) => {
    setParameters(prev => {
      // Éviter un update si les valeurs sont identiques
      if (
        prev.model === newParams.model_id &&
        prev.systemPrompt === newParams.system_prompt &&
        prev.temperature === newParams.temperature &&
        prev.maxTokens === newParams.max_tokens &&
        (prev as any).agentId === newParams.agent_id
      ) {
        return prev;
      }
      return {
        ...prev,
        model: newParams.model_id,
        systemPrompt: newParams.system_prompt,
        temperature: newParams.temperature,
        maxTokens: newParams.max_tokens,
        agentId: newParams.agent_id,
        agentName: newParams.name,
      };
    });
  }, []);

  // État vide: Pas de clé API
  if (!isLoadingKeys && keys.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-background p-8">
        <Card className="max-w-md border-border/50 bg-card/50 backdrop-blur-xl">
          <CardContent className="flex flex-col items-center text-center pt-12 pb-8 px-8">
            <div className="h-20 w-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
              <Key className="h-10 w-10 text-primary" />
            </div>
            
            <h2 className="text-xl font-bold text-foreground mb-2">
              Aucune Clé API
            </h2>
            
            <p className="text-muted-foreground mb-6">
              Créez votre première clé API pour configurer votre agent IA et commencer à utiliser le Playground.
            </p>
            
            <div className="space-y-3 w-full">
              <Link href="/keys">
                <Button className="w-full gap-2 bg-primary hover:bg-primary/90">
                  <Plus className="h-4 w-4" />
                  Créer ma première clé
                </Button>
              </Link>
              
              <p className="text-xs text-muted-foreground">
                Chaque clé API est liée à un agent unique avec son propre RAG et ses documents.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      {/* Main Playground Area (Middle) */}
      <div className="flex-1 flex flex-col min-w-0 bg-background">
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border/50 bg-card/30 backdrop-blur-md px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shadow-inner">
              <Terminal className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-foreground uppercase tracking-[0.2em]">Playground</h1>
                <Badge variant="outline" className="text-[9px] h-4 border-primary/20 bg-primary/5 text-primary font-bold">BETA</Badge>
              </div>
              <p className="text-[10px] text-muted-foreground font-medium flex items-center gap-1.5 mt-0.5">
                <Sparkles className="h-3 w-3 text-yellow-500" />
                ENVIRONNEMENT DE TEST ISOLÉ
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {!hasApiKey && (
              <Badge variant="outline" className="border-warning/30 bg-warning/5 text-warning text-[10px] px-2 py-0.5 font-bold animate-pulse">
                API KEY REQUISE
              </Badge>
            )}
            
            <div className="h-8 w-[1px] bg-border/50 mx-1 hidden sm:block" />

            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-9 px-3 text-xs gap-2 text-muted-foreground hover:text-destructive hover:bg-destructive/5 transition-colors"
                    onClick={newConversation}
                  >
                    <Eraser className="h-4 w-4" />
                    <span className="hidden md:inline">Effacer</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Effacer la conversation</TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="icon"
                    className={cn(
                      "h-9 w-9 text-muted-foreground hover:text-primary transition-all border-border/50",
                      !rightCollapsed && "bg-primary/5 text-primary border-primary/20"
                    )}
                    onClick={toggleRight}
                  >
                    <Settings2 
                      className={cn("h-4 w-4 transition-transform duration-300", !rightCollapsed && "rotate-90 text-primary")} 
                    />
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
              <div className="flex flex-col items-center justify-center pt-24 text-center space-y-6">
                <div className="relative">
                  <div className="absolute -inset-4 bg-primary/20 rounded-full blur-2xl animate-pulse" />
                  <div className="relative h-16 w-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border border-primary/10">
                    <Bot className="h-8 w-8 text-primary" />
                  </div>
                </div>
                <div className="space-y-2 max-w-sm">
                  <h3 className="text-base font-semibold text-foreground">Sandbox RAG Active</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Testez vos agents avec la recherche web, le RAG documentaire et des paramètres avancés dans cet environnement isolé.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 w-full max-w-md pt-4">
                  {[
                    { icon: Globe, text: "Web Search" },
                    { icon: ShieldCheck, text: "Strict RAG" },
                    { icon: Zap, text: "Fast Stream" },
                    { icon: Settings2, text: "Custom API" }
                  ].map((feat, i) => (
                    <div key={i} className="flex items-center gap-2 p-2.5 rounded-xl border border-border/50 bg-secondary/20 text-[10px] font-medium text-muted-foreground">
                      <feat.icon className="h-3.5 w-3.5 text-primary/70" />
                      {feat.text}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div 
                  key={message.id}
                  className={cn(
                    "flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300",
                    message.role === "user" ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <div className={cn(
                    "shrink-0 h-9 w-9 rounded-xl flex items-center justify-center shadow-sm",
                    message.role === "user" 
                      ? "bg-secondary text-secondary-foreground border border-border" 
                      : "bg-primary text-primary-foreground shadow-primary/20"
                  )}>
                    {message.role === "user" ? (
                      <User className="h-4.5 w-4.5" />
                    ) : (
                      <Bot className="h-4.5 w-4.5" />
                    )}
                  </div>
                  <div className={cn(
                    "flex-1 max-w-[85%] space-y-1.5",
                    message.role === "user" ? "items-end text-right" : "items-start text-left"
                  )}>
                    <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest px-1">
                      {message.role === "user" ? "Client Request" : "API Response"}
                    </div>
                    {message.isLoading ? (
                      <div className="space-y-2.5 p-4 rounded-2xl bg-secondary/30 border border-border/50">
                        <Skeleton className="h-3.5 w-full bg-primary/5" />
                        <Skeleton className="h-3.5 w-[80%] bg-primary/5" />
                        <Skeleton className="h-3.5 w-[60%] bg-primary/5" />
                      </div>
                    ) : (
                      <div className={cn(
                        "p-4 rounded-2xl text-sm leading-relaxed shadow-sm transition-all",
                        message.role === "user" 
                          ? "bg-secondary/50 border border-border text-foreground hover:bg-secondary/70" 
                          : "bg-card border border-border/50 text-foreground hover:border-primary/20"
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
        <div className="p-6 border-t border-border/50 bg-card/10 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-purple-500/20 rounded-2xl blur opacity-0 group-focus-within:opacity-100 transition duration-500" />
              <div className="relative">
                <Textarea 
                  placeholder="Posez une question à l'API..."
                  className="bg-secondary/40 border-border/50 min-h-[110px] pr-14 py-4 rounded-2xl custom-scrollbar focus-visible:ring-primary/40 focus-visible:border-primary/30 transition-all text-sm shadow-inner"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                />
                <Button 
                  size="icon"
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="absolute bottom-3 right-3 bg-primary hover:bg-primary/90 h-10 w-10 shadow-lg glow-brand rounded-xl"
                >
                  {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </Button>
              </div>
            </form>
            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground/70 font-mono">
                <span className="flex items-center gap-1.5">
                  <kbd className="px-1.5 py-0.5 bg-secondary border border-border/50 rounded text-[9px]">Enter</kbd> Envoyer
                </span>
                <span className="flex items-center gap-1.5 hidden sm:flex">
                  <kbd className="px-1.5 py-0.5 bg-secondary border border-border/50 rounded text-[9px]">Shift+Enter</kbd> Saut de ligne
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[9px] text-success font-bold tracking-tighter border-success/20 bg-success/5 animate-subtle-pulse">
                  STREAMING ACTIF
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Code Preview (Bottom) - Collapsible */}
        <CodePreview 
          parameters={parameters}
          requestContent={input}
          agentId={selectedKey?.agent_id}
          apiKey={selectedKey?.prefix}
        />
      </div>

      {/* Config Panel (Right) - Collapsible on desktop, hidden on mobile unless toggled */}
      <div 
        className={cn(
          "border-l border-border bg-card/40 backdrop-blur-xl overflow-hidden transition-all duration-300 ease-in-out h-full flex flex-col",
          "hidden lg:flex",
          rightCollapsed ? "lg:w-0 lg:border-l-0" : "lg:w-[340px]",
          !rightCollapsed && "fixed inset-y-0 right-0 w-[300px] z-50 lg:relative lg:inset-auto"
        )}
      >
        {!rightCollapsed && (
          <div className="flex-1 overflow-y-auto custom-scrollbar p-0">
            <div className="p-5 border-b border-border/50 bg-secondary/5 hidden lg:flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-widest text-foreground">Configuration</span>
            </div>
            <div className="p-4">
              <div className="flex items-center justify-between mb-4 lg:hidden">
                <h2 className="font-semibold text-sm">Configuration Agent</h2>
                <Button variant="ghost" size="icon" onClick={toggleRight}>
                  <PanelRightClose className="h-4 w-4" />
                </Button>
              </div>
              
              {/* Info sur la clé sélectionnée */}
              {selectedKey && (
                <div className="mb-4 p-3 rounded-lg bg-primary/5 border border-primary/10">
                  <div className="flex items-center gap-2 mb-1">
                    <Key className="h-4 w-4 text-primary" />
                    <span className="font-medium text-sm">{selectedKey.name}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Agent: {selectedKey.agent_name || "Non configuré"}
                  </p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {selectedKey.prefix}...
                  </p>
                </div>
              )}
              
              <AgentConfigPanel 
                onConfigChange={handleConfigChange}
                selectedAgentId={selectedKey?.agent_id}
                onAgentSelect={() => {}}
                onCreateAgent={async () => {}}
              />
            </div>
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
