"use client";

import React, { useState, useEffect } from "react";
import { Eye, EyeOff, Save, Loader2, Cpu, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ProviderConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  placeholder: string;
}

const providers: ProviderConfig[] = [
  { id: "openai", name: "OpenAI", description: "Utilisez GPT-4o, GPT-4, GPT-3.5", icon: "o", placeholder: "sk-..." },
  { id: "mistral", name: "Mistral AI", description: "Utilisez Mistral Large, Pixtral", icon: "m", placeholder: "..." },
  { id: "gemini", name: "Google Gemini", description: "Utilisez Gemini 1.5 Pro/Flash", icon: "g", placeholder: "..." },
  { id: "deepseek", name: "DeepSeek", description: "Le plus économique du marché", icon: "d", placeholder: "sk-..." },
];

export function ProvidersSection() {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState<string | null>(null);

  // Charger les clés du localStorage au montage
  useEffect(() => {
    const savedKeys: Record<string, string> = {};
    providers.forEach(p => {
      const key = localStorage.getItem(`byok_${p.id}`);
      if (key) savedKeys[p.id] = key;
    });
    setKeys(savedKeys);
  }, []);

  const handleSave = async (providerId: string) => {
    setIsSaving(providerId);
    try {
      // Simulation d'une latence réseau ou validation
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const key = keys[providerId];
      if (key) {
        localStorage.setItem(`byok_${providerId}`, key);
        toast.success(`Clé ${providerId} enregistrée localement`);
      } else {
        localStorage.removeItem(`byok_${providerId}`);
        toast.info(`Clé ${providerId} supprimée`);
      }
    } catch (error) {
      toast.error("Erreur lors de l'enregistrement");
    } finally {
      setIsSaving(null);
    }
  };

  const toggleShow = (id: string) => {
    setShowKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div>
        <h3 className="text-xl font-bold tracking-tight text-zinc-100">Fournisseurs de modèles (BYOK)</h3>
        <p className="text-sm text-zinc-400">
          Utilisez vos propres clés API pour ne payer que votre consommation réelle.
          Les clés sont stockées de manière sécurisée dans votre navigateur.
        </p>
      </div>

      <div className="grid gap-4">
        {providers.map((provider) => (
          <Card key={provider.id} className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm overflow-hidden group">
            <div className="flex flex-col md:flex-row md:items-center p-6 gap-6">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-zinc-800 border border-zinc-700 text-xl font-bold text-zinc-400 group-hover:border-indigo-500/50 transition-colors">
                {provider.icon.toUpperCase()}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-semibold text-zinc-100">{provider.name}</h4>
                  {keys[provider.id] && (
                    <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20 text-[10px]">
                      Configuré
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-zinc-500 truncate">{provider.description}</p>
              </div>

              <div className="flex flex-col md:flex-row gap-3 md:w-1/2 lg:w-2/5">
                <div className="relative flex-1">
                  <Input
                    type={showKeys[provider.id] ? "text" : "password"}
                    placeholder={provider.placeholder}
                    value={keys[provider.id] || ""}
                    onChange={(e) => setKeys(prev => ({ ...prev, [provider.id]: e.target.value }))}
                    className="bg-zinc-800 border-zinc-700 focus:border-indigo-500 pr-10 text-sm h-9"
                  />
                  <button
                    onClick={() => toggleShow(provider.id)}
                    className="absolute right-3 top-2.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {showKeys[provider.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <Button 
                  size="sm"
                  variant="outline"
                  onClick={() => handleSave(provider.id)}
                  disabled={isSaving === provider.id}
                  className="border-zinc-700 hover:bg-zinc-800 h-9 transition-all"
                >
                  {isSaving === provider.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  <span className="ml-2">Sauver</span>
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 flex gap-4">
        <AlertCircle className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-300/80 leading-relaxed">
          <strong>Note sur la sécurité :</strong> Vos clés API sont stockées localement (LocalStorage). 
          Elles ne transitent jamais par nos serveurs, sauf pour être transmises directement aux fournisseurs 
          de modèles lors de vos requêtes.
        </div>
      </div>
    </div>
  );
}
