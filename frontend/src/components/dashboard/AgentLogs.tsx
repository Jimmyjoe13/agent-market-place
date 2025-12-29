"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  RefreshCw,
  Search,
  FileText,
  Globe,
  MessageSquare,
  AlertTriangle,
  Clock,
  Zap,
} from "lucide-react";

// Types
interface AgentLog {
  id: string;
  created_at: string;
  endpoint: string;
  status_code: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens?: number;
  model_used?: string;
  routing_intent?: string;
  routing_confidence?: number;
  rag_context_found?: boolean;
  rag_sources_count: number;
  rag_context_preview?: string;
  llm_response_preview?: string;
  latency_ms?: number;
  error_type?: string;
  error_details?: string;
}

interface AgentLogsResponse {
  logs: AgentLog[];
  total: number;
}

// Intent configuration
const INTENT_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; color: string }> = {
  general: {
    icon: MessageSquare,
    label: "Général",
    color: "bg-gray-500/10 text-gray-600",
  },
  documents: {
    icon: FileText,
    label: "Documents",
    color: "bg-blue-500/10 text-blue-600",
  },
  web: {
    icon: Globe,
    label: "Web",
    color: "bg-green-500/10 text-green-600",
  },
  hybrid: {
    icon: Zap,
    label: "Hybride",
    color: "bg-purple-500/10 text-purple-600",
  },
  greeting: {
    icon: MessageSquare,
    label: "Salutation",
    color: "bg-yellow-500/10 text-yellow-600",
  },
};

interface AgentLogsProps {
  apiKeyId: string;
  apiKey: string;
  apiBaseUrl?: string;
}

/**
 * Tableau de logs détaillés pour debugging des requêtes d'un agent.
 */
export function AgentLogs({
  apiKeyId,
  apiKey,
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
}: AgentLogsProps) {
  const [intentFilter, setIntentFilter] = useState<string>("all");
  const [errorOnly, setErrorOnly] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AgentLog | null>(null);

  // Query pour récupérer les logs
  const {
    data,
    isLoading,
    refetch,
    isFetching,
  } = useQuery<AgentLogsResponse>({
    queryKey: ["agent-logs", apiKeyId, intentFilter, errorOnly],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "50" });
      if (intentFilter !== "all") {
        params.set("intent", intentFilter);
      }
      if (errorOnly) {
        params.set("error_only", "true");
      }

      const response = await fetch(
        `${apiBaseUrl}/api/v1/keys/${apiKeyId}/logs?${params}`,
        {
          headers: { "X-API-Key": apiKey },
        }
      );

      if (!response.ok) {
        // Fallback: retourner des données vides si l'endpoint n'existe pas encore
        return { logs: [], total: 0 };
      }

      return response.json();
    },
    enabled: !!apiKeyId && !!apiKey,
  });

  const logs = data?.logs || [];

  // Formater la date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  // Formater la latence
  const formatLatency = (ms?: number) => {
    if (!ms) return "—";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="h-5 w-5" />
            Logs de l'agent
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
        </div>

        {/* Filtres */}
        <div className="flex gap-4 mt-4">
          <Select value={intentFilter} onValueChange={setIntentFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filtrer par intent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les intents</SelectItem>
              <SelectItem value="general">Général</SelectItem>
              <SelectItem value="documents">Documents</SelectItem>
              <SelectItem value="web">Web</SelectItem>
              <SelectItem value="hybrid">Hybride</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant={errorOnly ? "destructive" : "outline"}
            size="sm"
            onClick={() => setErrorOnly(!errorOnly)}
          >
            <AlertTriangle className="h-4 w-4 mr-1" />
            {errorOnly ? "Erreurs uniquement" : "Toutes les requêtes"}
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Aucun log trouvé</p>
            <p className="text-sm">Les requêtes API apparaîtront ici</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">Date</TableHead>
                  <TableHead>Intent</TableHead>
                  <TableHead className="text-center">Sources</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">Latence</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => {
                  const intentConfig = INTENT_CONFIG[log.routing_intent || "general"] || INTENT_CONFIG.general;
                  const IntentIcon = intentConfig.icon;

                  return (
                    <TableRow
                      key={log.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelectedLog(log)}
                    >
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(log.created_at)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={intentConfig.color}>
                          <IntentIcon className="h-3 w-3 mr-1" />
                          {intentConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {log.rag_sources_count > 0 ? (
                          <Badge variant="secondary">
                            {log.rag_sources_count}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {log.prompt_tokens + log.completion_tokens}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`text-sm ${log.latency_ms && log.latency_ms > 3000 ? "text-yellow-600" : ""}`}>
                          {formatLatency(log.latency_ms)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        {log.error_type ? (
                          <Badge variant="destructive">Erreur</Badge>
                        ) : (
                          <Badge variant="outline" className="bg-green-500/10 text-green-600">
                            OK
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      {/* Dialog pour les détails */}
      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Détails de la requête</DialogTitle>
          </DialogHeader>
          {selectedLog && (
            <div className="space-y-4">
              {/* Métadonnées */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Date</p>
                  <p className="font-medium">{formatDate(selectedLog.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Modèle</p>
                  <p className="font-medium">{selectedLog.model_used || "N/A"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Latence</p>
                  <p className="font-medium">{formatLatency(selectedLog.latency_ms)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Tokens</p>
                  <p className="font-medium">
                    {selectedLog.prompt_tokens} + {selectedLog.completion_tokens} = {selectedLog.prompt_tokens + selectedLog.completion_tokens}
                  </p>
                </div>
              </div>

              {/* Contexte RAG */}
              {selectedLog.rag_context_preview && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Contexte RAG</p>
                  <pre className="text-sm bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap">
                    {selectedLog.rag_context_preview}
                  </pre>
                </div>
              )}

              {/* Réponse LLM */}
              {selectedLog.llm_response_preview && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Réponse LLM</p>
                  <pre className="text-sm bg-muted p-3 rounded-lg overflow-x-auto whitespace-pre-wrap">
                    {selectedLog.llm_response_preview}
                  </pre>
                </div>
              )}

              {/* Erreur */}
              {selectedLog.error_type && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <p className="text-sm font-medium text-red-600">{selectedLog.error_type}</p>
                  {selectedLog.error_details && (
                    <p className="text-sm text-red-500 mt-1">{selectedLog.error_details}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

export default AgentLogs;
