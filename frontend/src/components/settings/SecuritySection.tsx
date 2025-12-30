"use client";

import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Key, Shield, Eye, EyeOff, Save, Trash2, Loader2, Lock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { api } from "@/lib/api";
import { apiKeySchema, type ApiKeyFormData } from "@/lib/validations";

export function SecuritySection() {
  const [showKey, setShowKey] = useState(false);
  const [savedKey, setSavedKey] = useState<string | null>(null);

  const form = useForm<ApiKeyFormData>({
    resolver: zodResolver(apiKeySchema),
    defaultValues: {
      key: "",
    },
    mode: "onChange",
  });

  const { isSubmitting } = form.formState;

  useEffect(() => {
    const stored = api.getStoredApiKey();
    if (stored) {
      setSavedKey(stored);
      form.setValue("key", stored);
    }
  }, [form]);

  async function onSubmit(values: ApiKeyFormData) {
    const toastId = toast.loading("Vérification de la clé...");
    try {
      api.setApiKey(values.key);
      const health = await api.healthCheck();
      if (health.status === "healthy") {
        toast.success("Clé API configurée avec succès", { id: toastId });
        setSavedKey(values.key);
      } else {
        throw new Error("Backend inaccessible");
      }
    } catch (error) {
      api.clearApiKey();
      toast.error("Clé invalide ou erreur de connexion", { id: toastId });
    }
  }

  const handleClear = () => {
    api.clearApiKey();
    form.reset({ key: "" });
    setSavedKey(null);
    toast.info("Clé supprimée");
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div>
        <h3 className="text-xl font-bold tracking-tight text-zinc-100">Sécurité & Connexion</h3>
        <p className="text-sm text-zinc-400">Configurez votre clé d'accès principale au système RAG.</p>
      </div>

      <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Lock className="h-4 w-4 text-indigo-400" /> Clé Maîtresse (Console)
            </CardTitle>
            {savedKey && (
              <Badge className="bg-green-500/10 text-green-400 border-green-500/20">Active</Badge>
            )}
          </div>
          <CardDescription>
            Cette clé est nécessaire pour authentifier vos requêtes depuis la console vers le moteur RAG.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Clé API d'accès</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showKey ? "text" : "password"}
                          placeholder="rag_xxxxxxxxxxxxxxxx"
                          className="bg-zinc-800 border-zinc-700 focus:border-indigo-500 pr-10"
                          {...field}
                        />
                        <button
                          type="button"
                          onClick={() => setShowKey(!showKey)}
                          className="absolute right-3 top-2.5 text-zinc-500 hover:text-zinc-300"
                        >
                          {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={isSubmitting || !form.formState.isDirty} className="bg-indigo-600 hover:bg-indigo-500">
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                  Sauvegarder
                </Button>
                {savedKey && (
                  <Button type="button" variant="outline" onClick={handleClear} className="border-zinc-700 text-zinc-400 hover:text-red-400">
                    <Trash2 className="mr-2 h-4 w-4" /> Supprimer
                  </Button>
                )}
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/30">
          <CardHeader className="p-4">
            <CardTitle className="text-xs font-semibold uppercase text-zinc-500">Dernière Connexion</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <p className="text-sm text-zinc-300">Aujourd'hui à 12:45</p>
            <p className="text-[10px] text-zinc-500 mt-1">IP: 192.168.1.1 (Paris, FR)</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-900/30">
          <CardHeader className="p-4">
            <CardTitle className="text-xs font-semibold uppercase text-zinc-500">Double Authentification</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <Badge variant="outline" className="border-zinc-700 text-zinc-500">Désactivé</Badge>
            <Button variant="link" className="text-indigo-400 p-0 h-auto text-[10px] ml-2">Activer</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
