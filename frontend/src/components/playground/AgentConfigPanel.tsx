/**
 * Panneau de configuration de l'agent
 * Permet de modifier le modèle LLM, le prompt système et les options RAG
 */

'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useAgentConfigManager } from '@/hooks/useAgentConfig';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  Loader2, 
  Save, 
  Sparkles, 
  Brain, 
  Database, 
  Settings2, 
  Crown, 
  Zap,
  Flame,
  Maximize2,
  ChevronDown,
  Info
} from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from '@/lib/utils';

interface AgentConfigPanelProps {
  className?: string;
  onConfigChange?: (config: any) => void;
}

export default function AgentConfigPanel({ 
  className = '',
  onConfigChange 
}: AgentConfigPanelProps) {
  const { 
    config, 
    models, 
    isLoading, 
    isUpdating, 
    updateConfig 
  } = useAgentConfigManager();
  const { data: session } = useSession();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const userPlan = (session?.user as any)?.plan || 'free';
  const isPremium = userPlan !== 'free';

  // État local pour les modifications non sauvegardées
  const [localConfig, setLocalConfig] = useState({
    model_id: 'mistral-large-latest',
    system_prompt: '',
    rag_enabled: true,
    agent_name: '',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Synchroniser avec la config serveur
  useEffect(() => {
    if (config) {
      setLocalConfig({
        model_id: config.model_id,
        system_prompt: config.system_prompt || '',
        rag_enabled: config.rag_enabled,
        agent_name: config.agent_name || '',
        temperature: (config as any).temperature ?? 0.7,
        max_tokens: (config as any).max_tokens ?? 2048,
        top_p: (config as any).top_p ?? 1.0,
      });
      setHasChanges(false);
    }
  }, [config]);

  // Détecter les changements
  useEffect(() => {
    if (config) {
      const changed = 
        localConfig.model_id !== config.model_id ||
        localConfig.system_prompt !== (config.system_prompt || '') ||
        localConfig.rag_enabled !== config.rag_enabled ||
        localConfig.agent_name !== (config.agent_name || '') ||
        localConfig.temperature !== ((config as any).temperature ?? 0.7) ||
        localConfig.max_tokens !== ((config as any).max_tokens ?? 2048) ||
        localConfig.top_p !== ((config as any).top_p ?? 1.0);
      setHasChanges(changed);
      
      if (changed && onConfigChange) {
        onConfigChange(localConfig);
      }
    }
  }, [localConfig, config, onConfigChange]);

  const handleSave = () => {
    const updates: any = {};
    
    if (localConfig.model_id !== config?.model_id) {
      updates.model_id = localConfig.model_id;
    }
    if (localConfig.system_prompt !== (config?.system_prompt || '')) {
      updates.system_prompt = localConfig.system_prompt || null;
    }
    if (localConfig.rag_enabled !== config?.rag_enabled) {
      updates.rag_enabled = localConfig.rag_enabled;
    }
    if (localConfig.agent_name !== (config?.agent_name || '')) {
      updates.agent_name = localConfig.agent_name || null;
    }
    
    // Note: If backend supports these, add them to updates
    updates.temperature = localConfig.temperature;
    updates.max_tokens = localConfig.max_tokens;
    updates.top_p = localConfig.top_p;

    if (Object.keys(updates).length > 0) {
      updateConfig(updates);
    }
  };

  // Grouper les modèles par provider
  const modelsByProvider = models.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, typeof models>);

  if (isLoading) {
    return (
      <Card className={`${className} animate-pulse`}>
      <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Configuration Agent
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`${className} border-border/50 bg-card/50 backdrop-blur-sm`}>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Settings2 className="h-5 w-5 text-primary" />
          Configuration Agent
        </CardTitle>
        <CardDescription>
          Personnalisez le comportement de votre agent IA
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Sélection du modèle */}
        <div className="space-y-2" id="agent-model-select">
          <Label className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-purple-500" />
            Modèle LLM
          </Label>
          <Select
            value={localConfig.model_id}
            onValueChange={(value) => 
              setLocalConfig(prev => ({ ...prev, model_id: value }))
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Sélectionner un modèle" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(modelsByProvider).map(([provider, providerModels]) => (
                <div key={provider}>
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase">
                    {provider}
                  </div>
                  {providerModels.map((model) => (
                    <SelectItem 
                      key={model.id} 
                      value={model.id}
                      disabled={model.premium && !isPremium}
                    >
                      <div className="flex items-center gap-2">
                        <span>{model.name}</span>
                        {model.premium && (
                          <Badge 
                            variant="default" 
                            className={cn(
                              "text-xs text-white",
                              mounted && isPremium ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-zinc-700'
                            )}
                          >
                            <Crown className="h-3 w-3 mr-1" />
                            Premium
                          </Badge>
                        )}
                        {model.new && (
                          <Badge variant="outline" className="text-xs border-green-500 text-green-600">
                            <Zap className="h-3 w-3 mr-1" />
                            New
                          </Badge>
                        )}
                        {model.recommended && !model.premium && (
                          <Badge variant="secondary" className="text-xs">
                            <Sparkles className="h-3 w-3 mr-1" />
                            Recommandé
                          </Badge>
                        )}
                      </div>
                      {model.description && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {model.description}
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </div>
              ))}
            </SelectContent>
          </Select>
          {!isPremium && (
            <p className="text-[10px] text-amber-500 flex items-center gap-1">
              <Crown className="h-3 w-3" />
              Certains modèles nécessitent un abonnement Pro
            </p>
          )}
        </div>

        {/* Toggle RAG */}
        <div className="flex items-center justify-between" id="agent-rag-toggle">
          <div className="space-y-0.5">
            <Label className="flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              Recherche RAG
            </Label>
            <p className="text-xs text-muted-foreground">
              Chercher dans vos documents personnels
            </p>
          </div>
          <Switch
            checked={localConfig.rag_enabled}
            onCheckedChange={(checked) =>
              setLocalConfig(prev => ({ ...prev, rag_enabled: checked }))
            }
          />
        </div>

        {/* Prompt système */}
        <div className="space-y-3" id="agent-system-prompt">
          <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5 text-yellow-500" />
            Prompt Système
          </Label>
          <Textarea
            placeholder="Instructions personnalisées pour l'agent..."
            value={localConfig.system_prompt}
            onChange={(e) =>
              setLocalConfig(prev => ({ ...prev, system_prompt: e.target.value }))
            }
            className="min-h-[100px] bg-secondary/30 border-border/50 text-sm resize-none focus-visible:ring-primary/40"
          />
          <p className="text-[10px] text-muted-foreground italic">
            Laissez vide pour utiliser le prompt par défaut (expert en RAG).
          </p>
        </div>

        <Separator className="bg-border/50" />

        {/* Paramètres de Génération */}
        <div className="space-y-6">
          <div 
            className="flex items-center justify-between cursor-pointer group"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer group-hover:text-foreground transition-colors">
              <Settings2 className="h-3.5 w-3.5 text-primary" />
              Génération
            </Label>
            <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", showAdvanced && "rotate-180")} />
          </div>

          {showAdvanced && (
            <div className="space-y-6 animate-in fade-in slide-in-from-top-2 duration-300">
              {/* Temperature */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <Flame className="h-3.5 w-3.5 text-orange-500" />
                    Température
                  </Label>
                  <Badge variant="secondary" className="font-mono text-[10px] h-5 px-1.5">
                    {localConfig.temperature}
                  </Badge>
                </div>
                <Slider 
                  value={[localConfig.temperature]} 
                  min={0} 
                  max={2} 
                  step={0.1}
                  onValueChange={([v]) => setLocalConfig(prev => ({ ...prev, temperature: v }))}
                  className="[&_[role=slider]]:h-4 [&_[role=slider]]:w-4"
                />
                <p className="text-[10px] text-muted-foreground leading-tight">
                  Contrôle le caractère aléatoire. 0 est précis, 1+ est créatif.
                </p>
              </div>

              {/* Max Tokens */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <Maximize2 className="h-3.5 w-3.5 text-blue-500" />
                    Longueur Max
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Badge variant="secondary" className="font-mono text-[10px] h-5 px-1.5 flex items-center gap-1">
                          {localConfig.max_tokens}
                          <Info className="h-3 w-3 opacity-50" />
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent side="left" className="text-[10px]">
                        Tokens maximum dans la réponse
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <Slider 
                  value={[localConfig.max_tokens]} 
                  min={64} 
                  max={8192} 
                  step={64}
                  onValueChange={([v]) => setLocalConfig(prev => ({ ...prev, max_tokens: v }))}
                  className="[&_[role=slider]]:h-4 [&_[role=slider]]:w-4"
                />
              </div>
            </div>
          )}
        </div>

        {/* Bouton sauvegarder */}
        <Button
          onClick={handleSave}
          disabled={!hasChanges || isUpdating}
          className="w-full"
          id="agent-save-btn"
        >
          {isUpdating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {hasChanges ? 'Sauvegarder les modifications' : 'Aucune modification'}
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
