/**
 * Playground Parameters Panel (Collapsible)
 * ==========================================
 * 
 * Permet de configurer les paramètres de la requête LLM (Modèle, Température, etc.)
 * Version améliorée avec support collapse/expand et animation.
 */

"use client";

import { 
  Settings2, 
  Trash2, 
  HelpCircle,
  Cpu,
  Zap,
  Flame,
  Maximize2,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface PlaygroundParametersProps {
  parameters: {
    model: string;
    temperature: number;
    maxTokens: number;
    topP: number;
    systemPrompt: string;
  };
  setParameters: (params: any) => void;
  onReset: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function PlaygroundParameters({
  parameters,
  setParameters,
  onReset,
  isCollapsed = false,
  onToggleCollapse,
}: PlaygroundParametersProps) {
  const updateParam = (key: string, value: any) => {
    setParameters({ ...parameters, [key]: value });
  };

  // Version collapsed : barre étroite avec icônes seulement
  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full bg-zinc-900/50 border-r border-white/5 w-14 shrink-0">
        <div className="p-2 border-b border-white/5 flex flex-col items-center gap-2">
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 text-zinc-400 hover:text-primary"
                  onClick={onToggleCollapse}
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Ouvrir les paramètres</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        
        <div className="flex-1 flex flex-col items-center gap-3 py-4">
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Cpu className="h-4 w-4 text-primary" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">Modèle: {parameters.model}</p>
              </TooltipContent>
            </Tooltip>
            
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                  <Flame className="h-4 w-4 text-orange-400" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">Température: {parameters.temperature}</p>
              </TooltipContent>
            </Tooltip>
            
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Maximize2 className="h-4 w-4 text-blue-400" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">Max tokens: {parameters.maxTokens}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    );
  }

  // Version expanded : panneau complet
  return (
    <div className="flex flex-col h-full bg-zinc-900/50 border-r border-white/5 w-80 shrink-0 overflow-y-auto custom-scrollbar transition-all duration-300 ease-in-out">
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold text-sm">
          <Settings2 className="h-4 w-4 text-primary" />
          Settings
        </div>
        <div className="flex items-center gap-1">
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-8 w-8 text-zinc-500 hover:text-red-400"
            onClick={onReset}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          {onToggleCollapse && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8 text-zinc-500 hover:text-primary"
              onClick={onToggleCollapse}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="p-6 space-y-8">
        {/* Model Selection */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="h-3 w-3" />
              Model
            </Label>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <HelpCircle className="h-3 w-3 text-zinc-600" />
                </TooltipTrigger>
                <TooltipContent>Le modèle LLM à utiliser pour la génération</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Select 
            value={parameters.model} 
            onValueChange={(v: string) => updateParam("model", v)}
          >
            <SelectTrigger className="bg-zinc-950 border-white/10 h-9 text-sm">
              <SelectValue placeholder="Sélecteur de modèle" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-950 border-white/10">
              <SelectItem value="mistral-small">
                <div className="flex items-center gap-2">
                  <Zap className="h-3 w-3 text-yellow-500" />
                  Mistral Small
                </div>
              </SelectItem>
              <SelectItem value="mistral-medium">
                <div className="flex items-center gap-2">
                  <Zap className="h-3 w-3 text-orange-500" />
                  Mistral Medium
                </div>
              </SelectItem>
              <SelectItem value="mistral-large">
                <div className="flex items-center gap-2">
                  <Zap className="h-3 w-3 text-red-500" />
                  Mistral Large
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Separator className="bg-white/5" />

        {/* System Prompt */}
        <div className="space-y-3">
          <Label className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            System Prompt
          </Label>
          <Textarea 
            placeholder="Comportez-vous comme un expert en..."
            className="min-h-[120px] bg-zinc-950 border-white/10 text-sm resize-none focus-visible:ring-primary/50 placeholder:text-zinc-700"
            value={parameters.systemPrompt}
            onChange={(e) => updateParam("systemPrompt", e.target.value)}
          />
        </div>

        <Separator className="bg-white/5" />

        {/* Temperature */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <Flame className="h-3 w-3 text-orange-400" />
              Temperature
            </Label>
            <span className="text-xs font-mono text-zinc-500 bg-zinc-950 px-1.5 rounded border border-white/5">
              {parameters.temperature}
            </span>
          </div>
          <Slider 
            value={[parameters.temperature]} 
            min={0} 
            max={2} 
            step={0.1}
            onValueChange={([v]: number[]) => updateParam("temperature", v)}
            className="[&_[role=slider]]:bg-primary"
          />
          <p className="text-[10px] text-zinc-500 leading-tight">
            Contrôle le caractère aléatoire. 0 est déterministe, 1.0+ est créatif.
          </p>
        </div>

        {/* Max Tokens */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
              <Maximize2 className="h-3 w-3 text-blue-400" />
              Max Length
            </Label>
            <span className="text-xs font-mono text-zinc-500 bg-zinc-950 px-1.5 rounded border border-white/5">
              {parameters.maxTokens}
            </span>
          </div>
          <Slider 
            value={[parameters.maxTokens]} 
            min={64} 
            max={4096} 
            step={64}
            onValueChange={([v]: number[]) => updateParam("maxTokens", v)}
            className="[&_[role=slider]]:bg-primary"
          />
          <p className="text-[10px] text-zinc-500 leading-tight">
            Nombre maximum de tokens générés dans la réponse.
          </p>
        </div>

      </div>
    </div>
  );
}
