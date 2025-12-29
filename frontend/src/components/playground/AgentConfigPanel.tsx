/**
 * Panneau de configuration de l'agent
 * Permet de modifier le modèle LLM, le prompt système et les options RAG
 */

'use client';

import { useState, useEffect } from 'react';
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
import { Loader2, Save, Sparkles, Brain, Database, Settings } from 'lucide-react';

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

  // État local pour les modifications non sauvegardées
  const [localConfig, setLocalConfig] = useState({
    model_id: 'mistral-large-latest',
    system_prompt: '',
    rag_enabled: true,
    agent_name: '',
  });
  const [hasChanges, setHasChanges] = useState(false);

  // Synchroniser avec la config serveur
  useEffect(() => {
    if (config) {
      setLocalConfig({
        model_id: config.model_id,
        system_prompt: config.system_prompt || '',
        rag_enabled: config.rag_enabled,
        agent_name: config.agent_name || '',
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
        localConfig.agent_name !== (config.agent_name || '');
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
            <Settings className="h-5 w-5" />
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
          <Settings className="h-5 w-5 text-primary" />
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
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center gap-2">
                        <span>{model.name}</span>
                        {model.recommended && (
                          <Badge variant="secondary" className="text-xs">
                            <Sparkles className="h-3 w-3 mr-1" />
                            Recommandé
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
        <div className="space-y-2" id="agent-system-prompt">
          <Label className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-yellow-500" />
            Prompt Système
          </Label>
          <Textarea
            placeholder="Instructions personnalisées pour l'agent..."
            value={localConfig.system_prompt}
            onChange={(e) =>
              setLocalConfig(prev => ({ ...prev, system_prompt: e.target.value }))
            }
            className="min-h-[120px] resize-none"
          />
          <p className="text-xs text-muted-foreground">
            Laissez vide pour utiliser le prompt par défaut
          </p>
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
