"use client";

import { useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, Globe, Database, ChevronRight } from "lucide-react";

// Types for RAG sources
export interface RAGSource {
  content: string;
  source_type: string;
  source_id?: string;
  similarity?: number;
  metadata?: Record<string, unknown>;
}

interface SourcesDisplayProps {
  sources: RAGSource[];
  maxPreviewLength?: number;
  defaultExpanded?: boolean;
}

// Source type configuration
const SOURCE_TYPE_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; color: string }> = {
  pdf: {
    icon: FileText,
    label: "PDF",
    color: "bg-red-500/10 text-red-600 border-red-500/20",
  },
  github: {
    icon: Database,
    label: "GitHub",
    color: "bg-purple-500/10 text-purple-600 border-purple-500/20",
  },
  text: {
    icon: FileText,
    label: "Texte",
    color: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  },
  web: {
    icon: Globe,
    label: "Web",
    color: "bg-green-500/10 text-green-600 border-green-500/20",
  },
  default: {
    icon: FileText,
    label: "Document",
    color: "bg-gray-500/10 text-gray-600 border-gray-500/20",
  },
};

/**
 * Affiche une source RAG individuelle avec preview et métadonnées.
 */
function SourceCard({ source, maxPreviewLength = 300 }: { source: RAGSource; maxPreviewLength?: number }) {
  const [expanded, setExpanded] = useState(false);
  const config = SOURCE_TYPE_CONFIG[source.source_type] || SOURCE_TYPE_CONFIG.default;
  const SourceIcon = config.icon;

  const truncatedContent = source.content.length > maxPreviewLength
    ? source.content.slice(0, maxPreviewLength) + "..."
    : source.content;

  const similarityPercent = source.similarity
    ? Math.round(source.similarity * 100)
    : null;

  return (
    <Card className="border border-border/50 hover:border-border transition-colors">
      <CardContent className="p-3 space-y-2">
        {/* Header avec type et score */}
        <div className="flex items-center justify-between">
          <Badge variant="outline" className={`${config.color} text-xs`}>
            <SourceIcon className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
          {similarityPercent !== null && (
            <span className="text-xs text-muted-foreground">
              {similarityPercent}% match
            </span>
          )}
        </div>

        {/* Source ID si disponible */}
        {source.source_id && (
          <p className="text-xs text-muted-foreground truncate">
            📁 {source.source_id}
          </p>
        )}

        {/* Contenu */}
        <div 
          className="text-sm text-foreground/80 leading-relaxed cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? source.content : truncatedContent}
          {source.content.length > maxPreviewLength && (
            <button className="text-primary text-xs ml-1 hover:underline">
              {expanded ? "Réduire" : "Voir plus"}
            </button>
          )}
        </div>

        {/* Métadonnées si disponibles */}
        {source.metadata && Object.keys(source.metadata).length > 0 && (
          <div className="flex flex-wrap gap-1">
            {Object.entries(source.metadata).slice(0, 3).map(([key, value]) => (
              <span key={key} className="text-xs bg-secondary px-1.5 py-0.5 rounded">
                {key}: {String(value).slice(0, 20)}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Composant d'affichage des sources RAG utilisées dans une réponse.
 * 
 * S'intègre sous les réponses du chat/playground pour montrer
 * d'où viennent les informations de contexte.
 */
export function SourcesDisplay({
  sources,
  maxPreviewLength = 300,
  defaultExpanded = false,
}: SourcesDisplayProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Accordion
      type="single"
      collapsible
      defaultValue={defaultExpanded ? "sources" : undefined}
      className="mt-4"
    >
      <AccordionItem value="sources" className="border rounded-lg">
        <AccordionTrigger className="px-4 py-2 hover:no-underline">
          <div className="flex items-center gap-2 text-sm">
            <Database className="h-4 w-4 text-primary" />
            <span className="font-medium">
              📚 {sources.length} source{sources.length > 1 ? "s" : ""} utilisée{sources.length > 1 ? "s" : ""}
            </span>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">
          <div className="space-y-2">
            {sources.map((source, index) => (
              <SourceCard
                key={index}
                source={source}
                maxPreviewLength={maxPreviewLength}
              />
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

/**
 * Version inline plus compacte pour affichage dans les messages de chat.
 */
export function InlineSourcesIndicator({
  sources,
  onClick,
}: {
  sources: RAGSource[];
  onClick?: () => void;
}) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mt-2"
    >
      <Database className="h-3 w-3" />
      <span>{sources.length} source{sources.length > 1 ? "s" : ""}</span>
      <ChevronRight className="h-3 w-3" />
    </button>
  );
}

export default SourcesDisplay;
