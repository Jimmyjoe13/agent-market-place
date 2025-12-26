/**
 * Page des paramètres - Configuration de la clé API
 * Utilise React Hook Form + Zod pour la validation
 * et sonner pour les notifications
 */

"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Save, Eye, EyeOff, Loader2, Key, Server, Shield, Trash2, RefreshCw } from "lucide-react";
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
import { LoadingSpinner } from "@/components/ui/states";
import { api } from "@/lib/api";
import { apiKeySchema, type ApiKeyFormData } from "@/lib/validations";

export default function SettingsPage() {
  const [showKey, setShowKey] = useState(false);
  const [savedKey, setSavedKey] = useState<string | null>(null);

  const form = useForm<ApiKeyFormData>({
    resolver: zodResolver(apiKeySchema),
    defaultValues: {
      key: "",
    },
    mode: "onChange", // Validation en temps réel
  });

  const { isSubmitting } = form.formState;

  // Charger la clé stockée au montage
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
        toast.success("Clé API configurée", {
          id: toastId,
          description: "Connexion établie avec le backend.",
        });
        setSavedKey(values.key);
      } else {
        throw new Error("Backend non disponible");
      }
    } catch (error) {
      api.clearApiKey();
      toast.error("Clé invalide", {
        id: toastId,
        description: "Impossible de se connecter. Vérifiez votre clé API.",
      });
    }
  }

  const handleClear = () => {
    api.clearApiKey();
    form.reset({ key: "" });
    setSavedKey(null);
    toast.info("Clé supprimée", {
      description: "Votre clé API a été supprimée du stockage local.",
    });
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20">
              <Shield className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Paramètres</h1>
              <p className="text-zinc-400">Configurez votre accès à l&apos;API RAG Agent</p>
            </div>
          </div>
        </div>

        {/* API Key Card */}
        <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-indigo-400" />
              Clé API
              {savedKey && (
                <Badge variant="outline" className="ml-2 border-green-500/50 text-green-400">
                  Configurée
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Entrez votre clé API pour accéder aux fonctionnalités de l&apos;agent.
              Vous pouvez obtenir une clé auprès de l&apos;administrateur.
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
                      <FormLabel>Clé API *</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Input
                            type={showKey ? "text" : "password"}
                            placeholder="rag_xxxxxxxxxxxxxxxx"
                            className="bg-zinc-800 border-zinc-700 pr-10 focus:border-indigo-500"
                            disabled={isSubmitting}
                            {...field}
                          />
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="absolute right-0 top-0 h-full px-3 text-zinc-400 hover:text-zinc-100"
                            onClick={() => setShowKey(!showKey)}
                            disabled={isSubmitting}
                            tabIndex={-1}
                          >
                            {showKey ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </FormControl>
                      <FormDescription>
                        La clé doit commencer par &quot;rag_&quot;
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="flex gap-3">
                  <Button
                    type="submit"
                    disabled={!form.formState.isValid || isSubmitting}
                    className="gap-2 bg-indigo-600 hover:bg-indigo-500"
                  >
                    {isSubmitting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    {isSubmitting ? "Vérification..." : "Sauvegarder"}
                  </Button>

                  {savedKey && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleClear}
                      disabled={isSubmitting}
                      className="gap-2 border-zinc-700 hover:bg-zinc-800 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                      Supprimer
                    </Button>
                  )}
                </div>
              </form>
            </Form>

            {/* Help text */}
            <div className="mt-6 rounded-lg bg-zinc-800/50 p-4 text-sm text-zinc-400">
              <p className="mb-2 font-medium text-zinc-300">Comment obtenir une clé API ?</p>
              <ol className="list-inside list-decimal space-y-1">
                <li>Contactez l&apos;administrateur du système</li>
                <li>Demandez une clé avec les scopes nécessaires (query, feedback)</li>
                <li>Collez la clé ci-dessus et cliquez sur Sauvegarder</li>
              </ol>
            </div>
          </CardContent>
        </Card>

        {/* API Status Card */}
        <Card className="mt-6 border-zinc-800 bg-zinc-900/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-indigo-400" />
              État de l&apos;API
            </CardTitle>
            <CardDescription>
              Vérifiez la connexion avec le backend
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ApiStatus />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ===== API Status Component =====

function ApiStatus() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["api-health"],
    queryFn: async () => {
      const health = await api.healthCheck();
      return health;
    },
    refetchInterval: 30000, // Rafraîchir toutes les 30 secondes
    retry: 1,
  });

  const status = isLoading
    ? "loading"
    : isError
    ? "offline"
    : data?.status === "healthy"
    ? "online"
    : "offline";

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div
            className={`h-3 w-3 rounded-full transition-all ${
              status === "loading"
                ? "animate-pulse bg-zinc-500"
                : status === "online"
                ? "bg-green-500 shadow-lg shadow-green-500/20"
                : "bg-red-500 shadow-lg shadow-red-500/20"
            }`}
          />
          <span className="text-sm">
            {status === "loading"
              ? "Vérification..."
              : status === "online"
              ? "En ligne"
              : "Hors ligne"}
          </span>
        </div>
        {data?.version && (
          <Badge variant="outline" className="border-zinc-700 text-zinc-400">
            v{data.version}
          </Badge>
        )}
      </div>

      <Button
        size="sm"
        variant="ghost"
        onClick={() => refetch()}
        disabled={isLoading || isFetching}
        className="gap-2 text-zinc-400 hover:text-zinc-100"
      >
        {isFetching ? (
          <LoadingSpinner size="sm" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Actualiser
      </Button>
    </div>
  );
}
