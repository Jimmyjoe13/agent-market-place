/**
 * API Key Manager Component
 * =========================
 * 
 * Composant self-service pour la gestion des clés API.
 * UX inspirée de Stripe/OpenAI avec affichage unique de la clé.
 */

"use client";

import { useState, useCallback } from "react";
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  Eye,
  EyeOff,
  AlertTriangle,
  Clock,
  Zap,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useUserApiKeysManager } from "@/hooks/useUserApiKeys";
import type { ApiKeyInfo, ApiKeyResponse } from "@/types/api";

// ===== Types =====

interface CreateKeyFormData {
  name: string;
  scopes: string[];
  expiresInDays: number | null;
}

// ===== Subcomponents =====

function KeySecretDisplay({ 
  secretKey, 
  onClose 
}: { 
  secretKey: string; 
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(secretKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [secretKey]);

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-green-400">
            <Check className="h-5 w-5" />
            Clé API créée avec succès
          </DialogTitle>
          <DialogDescription className="text-zinc-400">
            Copiez cette clé maintenant. Pour des raisons de sécurité, elle ne sera plus jamais affichée.
          </DialogDescription>
        </DialogHeader>
        
        <div className="my-4">
          <div className="flex items-center gap-2 rounded-lg bg-zinc-800 p-3 font-mono text-sm">
            <code className="flex-1 break-all text-green-400">
              {secretKey}
            </code>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCopy}
              className="shrink-0 hover:bg-zinc-700"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-400" />
              ) : (
                <Copy className="h-4 w-4 text-zinc-400" />
              )}
            </Button>
          </div>
          
          <div className="mt-4 flex items-start gap-2 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-400">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <p>
              <strong>Important :</strong> Sauvegardez cette clé dans un endroit sécurisé.
              Vous ne pourrez plus la voir après avoir fermé cette fenêtre.
            </p>
          </div>
        </div>
        
        <DialogFooter>
          <Button onClick={handleCopy} variant="outline" className="border-zinc-700">
            {copied ? "Copié !" : "Copier la clé"}
          </Button>
          <Button onClick={onClose} className="bg-green-600 hover:bg-green-500">
            J&apos;ai sauvegardé ma clé
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function KeyRow({ 
  apiKey, 
  onRevoke,
  isRevoking,
}: { 
  apiKey: ApiKeyInfo; 
  onRevoke: (id: string) => void;
  isRevoking: boolean;
}) {
  const [showRevokeDialog, setShowRevokeDialog] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyPrefix = () => {
    navigator.clipboard.writeText(apiKey.prefix + "...");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (date: string | null | undefined) => {
    if (!date) return "Jamais";
    return new Date(date).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const isExpired = apiKey.expires_at && new Date(apiKey.expires_at) < new Date();

  return (
    <>
      <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 transition-colors hover:border-zinc-700">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10">
            <Key className="h-5 w-5 text-indigo-400" />
          </div>
          
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-zinc-100">{apiKey.name}</span>
              {!apiKey.is_active && (
                <Badge variant="destructive" className="text-xs">Révoquée</Badge>
              )}
              {isExpired && apiKey.is_active && (
                <Badge variant="secondary" className="text-xs bg-amber-500/20 text-amber-400">Expirée</Badge>
              )}
            </div>
            
            <div className="mt-1 flex items-center gap-3 text-sm text-zinc-500">
              <button
                onClick={handleCopyPrefix}
                className="font-mono hover:text-zinc-300 transition-colors flex items-center gap-1"
              >
                {apiKey.prefix}••••••••
                {copied ? (
                  <Check className="h-3 w-3 text-green-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
              
              <span className="text-zinc-600">•</span>
              
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDate(apiKey.last_used_at) === "Jamais" 
                  ? "Jamais utilisée" 
                  : `Dernière utilisation: ${formatDate(apiKey.last_used_at)}`
                }
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex flex-wrap gap-1">
            {apiKey.scopes.map((scope) => (
              <Badge 
                key={scope} 
                variant="outline" 
                className="text-xs border-zinc-700 text-zinc-400"
              >
                {scope}
              </Badge>
            ))}
          </div>
          
          <div className="flex items-center gap-1 text-sm text-zinc-500">
            <Zap className="h-3 w-3" />
            {apiKey.rate_limit_per_minute}/min
          </div>
          
          {apiKey.is_active && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowRevokeDialog(true)}
              className="text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      
      <AlertDialog open={showRevokeDialog} onOpenChange={setShowRevokeDialog}>
        <AlertDialogContent className="bg-zinc-900 border-zinc-800">
          <AlertDialogHeader>
            <AlertDialogTitle>Révoquer cette clé API ?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              Cette action est irréversible. Toutes les applications utilisant cette clé 
              cesseront de fonctionner immédiatement.
              <br /><br />
              <strong className="text-zinc-300">Clé :</strong> {apiKey.name} ({apiKey.prefix}...)
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-zinc-700 hover:bg-zinc-800">
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => onRevoke(apiKey.id)}
              className="bg-red-600 hover:bg-red-500"
              disabled={isRevoking}
            >
              {isRevoking ? "Révocation..." : "Révoquer la clé"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function CreateKeyDialog({
  open,
  onOpenChange,
  onSubmit,
  isCreating,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateKeyFormData) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["query"]);
  const [expiresInDays, setExpiresInDays] = useState<string>("never");

  const handleSubmit = () => {
    if (!name.trim()) return;
    
    onSubmit({
      name: name.trim(),
      scopes: selectedScopes,
      expiresInDays: expiresInDays === "never" ? null : parseInt(expiresInDays),
    });
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev, scope]
    );
  };

  const availableScopes = [
    { value: "query", label: "Query", description: "Interroger le RAG" },
    { value: "feedback", label: "Feedback", description: "Soumettre des feedbacks" },
    { value: "ingest", label: "Ingest", description: "Ingérer des documents" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle>Créer une nouvelle clé API</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Cette clé vous permettra d&apos;accéder à l&apos;API depuis vos applications.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nom de la clé</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ex: Production, Development, Mon App..."
              className="bg-zinc-800 border-zinc-700"
            />
          </div>
          
          <div className="space-y-2">
            <Label>Permissions</Label>
            <div className="flex flex-wrap gap-2">
              {availableScopes.map((scope) => (
                <button
                  key={scope.value}
                  onClick={() => toggleScope(scope.value)}
                  className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                    selectedScopes.includes(scope.value)
                      ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                      : "border-zinc-700 hover:border-zinc-600 text-zinc-400"
                  }`}
                >
                  {scope.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-zinc-500">
              Sélectionnez les permissions accordées à cette clé.
            </p>
          </div>
          
          <div className="space-y-2">
            <Label>Expiration</Label>
            <Select value={expiresInDays} onValueChange={setExpiresInDays}>
              <SelectTrigger className="bg-zinc-800 border-zinc-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-zinc-800 border-zinc-700">
                <SelectItem value="never">Jamais</SelectItem>
                <SelectItem value="30">30 jours</SelectItem>
                <SelectItem value="90">90 jours</SelectItem>
                <SelectItem value="180">6 mois</SelectItem>
                <SelectItem value="365">1 an</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-zinc-700"
          >
            Annuler
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!name.trim() || selectedScopes.length === 0 || isCreating}
            className="bg-indigo-600 hover:bg-indigo-500"
          >
            {isCreating ? "Création..." : "Créer la clé"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ===== Main Component =====

export function ApiKeyManager() {
  const {
    keys,
    total,
    isLoading,
    isCreating,
    isRevoking,
    createKey,
    revokeKey,
    refresh,
    lastCreatedKey,
    resetLastCreatedKey,
    error,
    isError,
  } = useUserApiKeysManager();

  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const handleCreate = async (data: CreateKeyFormData) => {
    try {
      await createKey({
        name: data.name,
        scopes: data.scopes,
        expires_in_days: data.expiresInDays ?? undefined,
      });
      setShowCreateDialog(false);
    } catch {
      // Error handled by hook
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await revokeKey(keyId);
    } catch {
      // Error handled by hook
    }
  };

  if (isLoading) {
    return (
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardContent className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-zinc-500" />
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400 mb-4" />
          <h3 className="font-medium text-red-400">Erreur de chargement</h3>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : "Impossible de charger les clés API"}
          </p>
          <Button onClick={() => refresh()} variant="outline" className="mt-4 border-zinc-700">
            Réessayer
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-indigo-400" />
              Clés API
            </CardTitle>
            <CardDescription>
              Gérez vos clés d&apos;accès à l&apos;API. {total > 0 && `${total} clé(s) active(s).`}
            </CardDescription>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="bg-indigo-600 hover:bg-indigo-500"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nouvelle clé
          </Button>
        </CardHeader>
        
        <CardContent>
          {keys.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800 mb-4">
                <Key className="h-8 w-8 text-zinc-600" />
              </div>
              <h3 className="font-medium text-zinc-300">Aucune clé API</h3>
              <p className="text-sm text-zinc-500 mt-2 max-w-sm">
                Créez votre première clé API pour commencer à utiliser l&apos;API dans vos applications.
              </p>
              <Button
                onClick={() => setShowCreateDialog(true)}
                className="mt-4 bg-indigo-600 hover:bg-indigo-500"
              >
                <Plus className="h-4 w-4 mr-2" />
                Créer ma première clé
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {keys.map((apiKey) => (
                <KeyRow
                  key={apiKey.id}
                  apiKey={apiKey}
                  onRevoke={handleRevoke}
                  isRevoking={isRevoking}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      
      <CreateKeyDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSubmit={handleCreate}
        isCreating={isCreating}
      />
      
      {lastCreatedKey?.key && (
        <KeySecretDisplay
          secretKey={lastCreatedKey.key}
          onClose={resetLastCreatedKey}
        />
      )}
    </>
  );
}

export default ApiKeyManager;
