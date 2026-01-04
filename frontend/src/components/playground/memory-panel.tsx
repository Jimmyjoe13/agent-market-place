/**
 * Panneau d'affichage de la mémoire conversationnelle d'un agent
 * 
 * Affiche l'historique des messages en mémoire avec:
 * - Liste des messages user/assistant
 * - Statistiques (nombre, dates)
 * - Action pour effacer la mémoire
 */

'use client';

import { useState } from 'react';
import { Brain, Trash2, RefreshCw, ChevronDown, ChevronUp, User, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useAgentMemory, MemoryMessage } from '@/hooks/useAgentMemory';

interface MemoryPanelProps {
  agentId: string | null;
  className?: string;
}

export function MemoryPanel({ agentId, className }: MemoryPanelProps) {
  const [isOpen, setIsOpen] = useState(true);
  const {
    messages,
    stats,
    memoryLimit,
    agentName,
    isLoading,
    isClearing,
    clearMemory,
    refetch,
  } = useAgentMemory(agentId);

  // Formatage de la date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '-';
    }
  };

  // Tronquer le contenu pour l'affichage
  const truncateContent = (content: string, maxLength: number = 150) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  if (!agentId) {
    return null;
  }

  return (
    <Card className={cn('border-muted', className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Mémoire Agent</CardTitle>
              <Badge variant="secondary" className="ml-2">
                {stats.count}/{memoryLimit}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => refetch()}
                disabled={isLoading}
                title="Rafraîchir"
              >
                <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
              </Button>

              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    disabled={stats.count === 0 || isClearing}
                    title="Effacer la mémoire"
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Effacer la mémoire ?</AlertDialogTitle>
                    <AlertDialogDescription>
                      Cette action supprimera définitivement les {stats.count} messages 
                      en mémoire de l'agent "{agentName}". L'agent oubliera tout l'historique 
                      de conversation.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Annuler</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => clearMemory()}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Effacer
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="icon">
                  {isOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
          <CardDescription>
            Historique des conversations mémorisées
          </CardDescription>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : stats.count === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Brain className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Aucun message en mémoire</p>
                <p className="text-sm mt-1">
                  L'agent commencera à mémoriser après vos premières conversations.
                </p>
              </div>
            ) : (
              <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-3">
                  {messages.map((message: MemoryMessage, index: number) => (
                    <div
                      key={message.id}
                      className={cn(
                        'flex gap-3 p-3 rounded-lg',
                        message.role === 'user'
                          ? 'bg-muted/50'
                          : 'bg-primary/5 border border-primary/10'
                      )}
                    >
                      <div
                        className={cn(
                          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                          message.role === 'user'
                            ? 'bg-muted-foreground/20'
                            : 'bg-primary/20'
                        )}
                      >
                        {message.role === 'user' ? (
                          <User className="h-4 w-4" />
                        ) : (
                          <Bot className="h-4 w-4 text-primary" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium">
                            {message.role === 'user' ? 'Vous' : 'Agent'}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(message.created_at)}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-3">
                          {truncateContent(message.content)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            {/* Stats footer */}
            {stats.count > 0 && (
              <div className="mt-4 pt-4 border-t flex justify-between text-xs text-muted-foreground">
                <span>Premier message: {formatDate(stats.oldest_message)}</span>
                <span>Dernier message: {formatDate(stats.newest_message)}</span>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export default MemoryPanel;
