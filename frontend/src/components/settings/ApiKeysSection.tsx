"use client";

import React, { useState, useEffect } from "react";
import { Plus, Trash2, Shield, Key, Copy, Check, Loader2, AlertTriangle, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ApiKeyInfo } from "@/types/api";

export function ApiKeysSection() {
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      const response = await api.getUserApiKeys();
      setKeys(response.keys);
    } catch (error) {
      toast.error("Échec de la récupération des clés API");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCopy = (key: string, id: string) => {
    navigator.clipboard.writeText(key);
    setCopiedId(id);
    toast.success("Clé API copiée");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Êtes-vous sûr de vouloir révoquer cette clé ? Elle ne pourra plus être utilisée.")) return;
    
    try {
      await api.revokeUserApiKey(id);
      toast.success("Clé API révoquée");
      setKeys(keys.filter(k => k.id !== id));
    } catch (error) {
      toast.error("Échec de la révocation");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-zinc-100">Clés API RAG</h3>
          <p className="text-sm text-zinc-400">Gérez vos clés d'accès programmatiques pour l'API RAG.</p>
        </div>
        <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20">
          <Plus className="mr-2 h-4 w-4" /> Nouvelle Clé
        </Button>
      </div>

      <div className="grid gap-4">
        {keys.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 rounded-xl border-2 border-dashed border-zinc-800 bg-zinc-900/20">
            <Key className="h-12 w-12 text-zinc-700 mb-4" />
            <p className="text-zinc-400 text-sm">Vous n'avez pas encore de clé API.</p>
          </div>
        ) : (
          keys.map((key) => (
            <Card key={key.id} className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm transition-all hover:bg-zinc-900/80">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-zinc-800 border border-zinc-700">
                      <Shield className="h-5 w-5 text-indigo-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-zinc-100 text-sm">{key.name}</span>
                        {!key.is_active && (
                          <Badge variant="outline" className="border-red-500/50 text-red-500 text-[10px] py-0">Révoquée</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 font-mono text-xs text-zinc-500">
                        <code>{key.prefix}••••••••••••</code>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] text-zinc-500">
                      Créée le {new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(key.created_at))}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button 
                        size="icon" 
                        variant="ghost" 
                        className="h-8 w-8 text-zinc-400 hover:text-white"
                        onClick={() => handleCopy(key.id, key.id)} // In a real app we'd have the secret here
                      >
                        {copiedId === key.id ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                      </Button>
                      <Button 
                        size="icon" 
                        variant="ghost" 
                        className="h-8 w-8 text-zinc-400 hover:text-red-400"
                        onClick={() => handleRevoke(key.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-zinc-800 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                  {key.scopes.map(scope => (
                    <Badge key={scope} variant="secondary" className="bg-zinc-800 text-zinc-400 text-[10px] whitespace-nowrap">
                      {scope}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <Card className="bg-orange-500/5 border-orange-500/20">
        <CardContent className="p-4 flex gap-4">
          <AlertTriangle className="h-5 w-5 text-orange-500 shrink-0 mt-0.5" />
          <div className="text-xs text-orange-200/80 space-y-2">
            <p className="font-semibold">Protégez vos clés !</p>
            <p>
              Toute personne possédant votre clé API peut accéder à vos ressources RAG. 
              Ne partagez jamais vos clés et ne les exposez pas dans du code frontend public.
            </p>
            <a href="/docs/api" className="inline-flex items-center text-orange-400 hover:underline gap-1">
              Consulter la documentation API <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
