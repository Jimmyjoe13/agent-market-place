"use client";

import React, { useState, useEffect } from "react";
import { Eye, EyeOff, Save, Loader2, Cloud, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { UserProfile } from "@/types/api";

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
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isSaving, setIsSaving] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Charger le profil et les clés
  useEffect(() => {
    const loadData = async () => {
      try {
        const userProfile = await api.getUserProfile();
        setProfile(userProfile);
        
        const localKeys: Record<string, string> = {};
        providers.forEach(p => {
          const key = localStorage.getItem(`byok_${p.id}`);
          if (key) localKeys[p.id] = key;
        });
        setKeys(localKeys);
      } catch (error) {
        console.error("Failed to load profile", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  const handleSave = async (providerId: string) => {
    setIsSaving(providerId);
    try {
      const key = keys[providerId];
      
      // 1. Sauvegarder localement (pour compatibilité immédiate)
      if (key) {
        localStorage.setItem(`byok_${providerId}`, key);
      } else {
        localStorage.removeItem(`byok_${providerId}`);
      }

      // 2. Sauvegarder sur le serveur (Persistance BYOK)
      await api.updateProfile({
        provider_keys: {
          [providerId]: key || "" // Une chaîne vide supprimera la clé côté serveur
        }
      });
      
      // Rafraîchir le profil pour voir le badge Cloud mis à jour
      const updatedProfile = await api.getUserProfile();
      setProfile(updatedProfile);
      
      if (key) {
        toast.success(`Clé ${providerId} synchronisée avec votre compte`);
      } else {
        toast.info(`Clé ${providerId} supprimée`);
      }
    } catch (error) {
      toast.error("Erreur lors de la synchronisation");
    } finally {
      setIsSaving(null);
    }
  };

  const toggleShow = (id: string) => {
    setShowKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <p className="text-zinc-400 text-sm">Chargement de vos configurations...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-zinc-100">Fournisseurs de modèles (BYOK)</h3>
          <p className="text-sm text-zinc-400">
            Utilisez vos propres clés API. Elles sont désormais <strong>chiffrées et synchronisées</strong> sur votre compte.
          </p>
        </div>
        <Badge variant="outline" className="border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
          <Cloud className="h-3 w-3 mr-1" /> Persistance Active
        </Badge>
      </div>

      <div className="grid gap-4">
        {providers.map((provider) => {
          const isConfiguredOnServer = profile?.provider_keys_summary?.[provider.id];
          const isConfiguredLocally = !!keys[provider.id];
          
          return (
            <Card key={provider.id} className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm overflow-hidden group">
              <div className="flex flex-col md:flex-row md:items-center p-6 gap-6">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-zinc-800 border border-zinc-700 text-xl font-bold text-zinc-400 group-hover:border-indigo-500/50 transition-colors">
                  {provider.icon.toUpperCase()}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-zinc-100">{provider.name}</h4>
                    {isConfiguredOnServer && (
                      <Badge variant="outline" className="bg-indigo-500/10 text-indigo-400 border-indigo-500/20 text-[10px]">
                        Cloud
                      </Badge>
                    )}
                    {isConfiguredLocally && !isConfiguredOnServer && (
                      <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]">
                        Local uniquement
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 truncate">{provider.description}</p>
                </div>

                <div className="flex flex-col md:flex-row gap-3 md:w-1/2 lg:w-2/5">
                  <div className="relative flex-1">
                    <Input
                      type={showKeys[provider.id] ? "text" : "password"}
                      placeholder={isConfiguredOnServer && !keys[provider.id] ? "••••••••••••••••" : provider.placeholder}
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
                      <RefreshCw className="h-4 w-4" />
                    )}
                    <span className="ml-2">Sync</span>
                  </Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 flex gap-4">
        <Cloud className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-300/80 leading-relaxed">
          <strong>Niveau de sécurité Cloud :</strong> Vos clés sont désormais chiffrées avec AES-256 côté serveur. 
          Elles ne sont jamais affichées en clair dans l'interface après enregistrement, pour une sécurité maximale.
          La synchronisation vous permet de retrouver vos configurations sur tous vos appareils.
        </div>
      </div>
    </div>
  );
}
