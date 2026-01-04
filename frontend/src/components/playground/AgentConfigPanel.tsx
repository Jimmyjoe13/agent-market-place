/**
 * Panneau de configuration de l'agent (Multi-Agent Version)
 * Permet de sélectionner, créer et configurer les agents.
 */

'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useAgents } from '@/hooks/useAgents';
import { useAvailableModels } from '@/hooks/useAgentConfig';
import { CreateAgentDialog } from './CreateAgentDialog';
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
import { Input } from '@/components/ui/input';
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
  Info,
  Plus,
  Bot,
  Globe
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
  selectedAgentId?: string | null;
  onAgentSelect?: (id: string) => void;
  onCreateAgent?: (data: { name: string; description?: string }) => Promise<void>;
}

export default function AgentConfigPanel({ 
  className = '',
  onConfigChange,
  selectedAgentId,
  onAgentSelect,
  onCreateAgent
}: AgentConfigPanelProps) {
  // Hooks
  const { 
    agents, 
    selectedAgent, 
    // activeKey, // Pas besoin ici
    createAgent, // Fallback si onCreateAgent n'est pas fourni (optionnel)
    updateAgent,
    isLoading: isLoadingAgents, 
    isUpdating,
    isCreating
  } = useAgents(selectedAgentId || undefined);
  
  const { data: models = [], isLoading: isLoadingModels } = useAvailableModels();
  const { user } = useAuth();
  
  const [mounted, setMounted] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // État local pour le formulaire
  const [localConfig, setLocalConfig] = useState({
    name: '',
    description: '',
    model_id: 'mistral-large-latest',
    system_prompt: '',
    rag_enabled: true,
    use_web_search: true,
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
  });
  
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const userPlan = user?.user_metadata?.plan || 'free';
  const isPremium = userPlan !== 'free';

  // Synchroniser l'état local quand l'agent sélectionné change
  useEffect(() => {
    if (selectedAgent) {
      setLocalConfig(prev => ({
        name: selectedAgent.name,
        description: selectedAgent.description || '',
        model_id: selectedAgent.model_id,
        system_prompt: selectedAgent.system_prompt || '',
        rag_enabled: selectedAgent.rag_enabled,
        use_web_search: prev.use_web_search, // Préserver la préférence de session
        temperature: selectedAgent.temperature ?? 0.7,
        max_tokens: selectedAgent.max_monthly_tokens > 0 ? 0 : 2048,
        top_p: 1.0,
      }));
      setHasChanges(false);
    }
  }, [selectedAgent]);

  // Détecter les changements et notifier le parent
  useEffect(() => {
    if (selectedAgent) {
      const changed = 
        localConfig.name !== selectedAgent.name ||
        localConfig.description !== (selectedAgent.description || '') ||
        localConfig.model_id !== selectedAgent.model_id ||
        localConfig.system_prompt !== (selectedAgent.system_prompt || '') ||
        localConfig.rag_enabled !== selectedAgent.rag_enabled ||
        localConfig.temperature !== (selectedAgent.temperature ?? 0.7);
      
      setHasChanges(changed);
      
      if (onConfigChange) {
        onConfigChange({
            ...localConfig,
            agent_id: selectedAgent.id
        });
      }
    }
  }, [localConfig, selectedAgent, onConfigChange]);

  const handleSave = async () => {
    if (!selectedAgentId) return;

    const updates: any = {};
    if (localConfig.name !== selectedAgent?.name) updates.name = localConfig.name;
    if (localConfig.description !== (selectedAgent?.description || '')) updates.description = localConfig.description;
    if (localConfig.model_id !== selectedAgent?.model_id) updates.model_id = localConfig.model_id;
    if (localConfig.system_prompt !== (selectedAgent?.system_prompt || '')) updates.system_prompt = localConfig.system_prompt;
    if (localConfig.rag_enabled !== selectedAgent?.rag_enabled) updates.rag_enabled = localConfig.rag_enabled;
    if (localConfig.temperature !== selectedAgent?.temperature) updates.temperature = localConfig.temperature;

    if (Object.keys(updates).length > 0) {
      await updateAgent({ id: selectedAgentId, updates });
    }
  };

  const handleCreateAgent = async (data: { name: string; description?: string }) => {
    if (onCreateAgent) {
        await onCreateAgent(data);
    } else {
        // Fallback local
        const newAgent = await createAgent({
            ...data,
            model_id: 'mistral-large-latest',
            rag_enabled: true,
            temperature: 0.7
        });
        if (onAgentSelect) onAgentSelect(newAgent.id);
    }
  };

  // Grouper les modèles par provider
  const modelsByProvider = models.reduce((acc: any, model: any) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, typeof models>);

  const isLoading = isLoadingAgents || isLoadingModels;

  if (isLoading && !selectedAgent) {
    return (
      <Card className={`${className} animate-pulse`}>
        <CardHeader>
          <CardTitle>Chargement...</CardTitle>
        </CardHeader>
        <CardContent className="h-64 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`${className} border-border/50 bg-card/50 backdrop-blur-sm flex flex-col h-full`}>
      <CardHeader className="pb-4 shrink-0">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Settings2 className="h-5 w-5 text-primary" />
              Configuration
            </CardTitle>
            <CreateAgentDialog 
                onCreate={handleCreateAgent}
                trigger={
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Plus className="h-4 w-4" />
                    </Button>
                }
            />
          </div>

          {/* SÉLECTEUR D'AGENT */}
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground uppercase font-semibold tracking-wider">
                Agent Actif
            </Label>
            <Select 
                value={selectedAgentId || ''} 
                onValueChange={(val) => onAgentSelect && onAgentSelect(val)}
                disabled={isLoadingAgents}
            >
                <SelectTrigger className="w-full bg-secondary/50 border-primary/20 focus:ring-primary/20 h-10">
                    <SelectValue placeholder="Sélectionner un agent" />
                </SelectTrigger>
                <SelectContent>
                    {agents.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id} className="cursor-pointer">
                            <div className="flex items-center gap-2">
                                <div className="h-5 w-5 rounded-md bg-primary/10 flex items-center justify-center">
                                    <Bot className="h-3 w-3 text-primary" />
                                </div>
                                <span className="font-medium">{agent.name}</span>
                            </div>
                        </SelectItem>
                    ))}
                    {agents.length === 0 && (
                        <div className="p-2 text-xs text-center text-muted-foreground">
                            Aucun agent. Créez-en un !
                        </div>
                    )}
                </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar px-6 pb-6">
        <CardContent className="p-0 space-y-6">
            
            {/* Identité Agent (Nom/Desc) */}
            <div className="space-y-3">
                <div className="grid gap-2">
                    <Label>Nom</Label>
                    <Input 
                        value={localConfig.name} 
                        onChange={e => setLocalConfig(prev => ({ ...prev, name: e.target.value }))}
                        className="bg-secondary/30"
                    />
                </div>
                <div className="grid gap-2">
                    <Label>Description</Label>
                    <Input 
                        value={localConfig.description} 
                        onChange={e => setLocalConfig(prev => ({ ...prev, description: e.target.value }))}
                        className="bg-secondary/30 text-xs"
                        placeholder="Description courte..."
                    />
                </div>
            </div>

            <Separator className="bg-border/50" />

          {/* Sélection du modèle */}
          <div className="space-y-2">
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
                {Object.entries(modelsByProvider).map(([provider, providerModels]: [string, any]) => (
                  <div key={provider}>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase">
                      {provider}
                    </div>
                    {providerModels.map((model: any) => (
                      <SelectItem 
                        key={model.id} 
                        value={model.id}
                        disabled={model.premium && !isPremium}
                      >
                        <div className="flex items-center gap-2">
                          <span>{model.name}</span>
                          {model.premium && (
                            <Badge variant="secondary" className="text-[10px] h-4 px-1 bg-gradient-brand text-white border-0">
                              PRO
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Toggle RAG */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-secondary/10">
            <div className="space-y-0.5">
              <Label className="flex items-center gap-2 text-sm">
                <Database className="h-4 w-4 text-blue-500" />
                RAG Knowledge
              </Label>
              <p className="text-[10px] text-muted-foreground">
                Accès aux documents
              </p>
            </div>
            <Switch
              checked={localConfig.rag_enabled}
              onCheckedChange={(checked) =>
                setLocalConfig(prev => ({ ...prev, rag_enabled: checked }))
              }
            />
          </div>

          {/* Toggle Web Search */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-secondary/10">
            <div className="space-y-0.5">
              <Label className="flex items-center gap-2 text-sm">
                <Globe className="h-4 w-4 text-emerald-500" />
                Recherche Web
              </Label>
              <p className="text-[10px] text-muted-foreground">
                Recherche temps réel
              </p>
            </div>
            <Switch
              checked={localConfig.use_web_search}
              onCheckedChange={(checked) =>
                setLocalConfig(prev => ({ ...prev, use_web_search: checked }))
              }
            />
          </div>

          {/* Prompt système */}
          <div className="space-y-3">
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
              className="min-h-[120px] bg-secondary/30 border-border/50 text-sm resize-none focus-visible:ring-primary/40 leading-relaxed"
            />
          </div>

          {/* Paramètres Avancés */}
          <div className="space-y-6 pt-2">
            <div 
              className="flex items-center justify-between cursor-pointer group hover:bg-secondary/20 p-2 rounded-lg transition-colors -mx-2"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <Label className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer">
                <Settings2 className="h-3.5 w-3.5 text-primary" />
                Paramètres Avancés
              </Label>
              <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", showAdvanced && "rotate-180")} />
            </div>

            {showAdvanced && (
              <div className="space-y-6 animate-in fade-in slide-in-from-top-2 duration-300 pl-2 border-l-2 border-border/50 ml-1">
                {/* Temperature */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <Flame className="h-3.5 w-3.5 text-orange-500" />
                      Température: {localConfig.temperature}
                    </Label>
                  </div>
                  <Slider 
                    value={[localConfig.temperature]} 
                    min={0} 
                    max={2} 
                    step={0.1}
                    onValueChange={([v]) => setLocalConfig(prev => ({ ...prev, temperature: v }))}
                    className="[&_[role=slider]]:h-4 [&_[role=slider]]:w-4"
                  />
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </div>

      {/* Footer sticky avec bouton sauvegarder */}
      <div className="p-6 border-t border-border/50 bg-card/50 backdrop-blur-xl mt-auto">
        <Button
          onClick={handleSave}
          disabled={!hasChanges || isUpdating}
          className="w-full shadow-lg shadow-primary/10"
          size="lg"
        >
          {isUpdating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {hasChanges ? 'Sauvegarder les modifications' : 'Tout est à jour'}
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}

