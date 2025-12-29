"use client";

import { useState, useCallback } from "react";
import { Check, Copy, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Types
interface DynamicCodeSnippetProps {
  apiKey?: string;
  agentName?: string;
  endpoint?: string;
  baseUrl?: string;
}

type Language = "python" | "javascript" | "curl";

// Code templates
const CODE_TEMPLATES: Record<Language, (config: { apiKey: string; baseUrl: string; endpoint: string }) => string> = {
  python: ({ apiKey, baseUrl, endpoint }) => `import requests

# Configuration
API_KEY = "${apiKey}"
BASE_URL = "${baseUrl}"

# Headers avec clé API
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Requête au RAG
response = requests.post(
    f"{BASE_URL}${endpoint}",
    headers=headers,
    json={
        "question": "Quelles sont les informations dans mes documents?",
        "use_rag": True,
        "enable_reflection": False
    }
)

# Résultat
data = response.json()
print(f"Réponse: {data['answer']}")
print(f"Sources: {len(data.get('sources', []))} trouvée(s)")`,

  javascript: ({ apiKey, baseUrl, endpoint }) => `// Configuration
const API_KEY = "${apiKey}";
const BASE_URL = "${baseUrl}";

// Requête au RAG
async function queryRAG(question) {
  const response = await fetch(\`\${BASE_URL}${endpoint}\`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      use_rag: true,
      enable_reflection: false,
    }),
  });

  const data = await response.json();
  return data;
}

// Utilisation
queryRAG("Quelles sont les informations dans mes documents?")
  .then((data) => {
    console.log("Réponse:", data.answer);
    console.log("Sources:", data.sources?.length || 0);
  })
  .catch(console.error);`,

  curl: ({ apiKey, baseUrl, endpoint }) => `curl -X POST "${baseUrl}${endpoint}" \\
  -H "X-API-Key: ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Quelles sont les informations dans mes documents?",
    "use_rag": true,
    "enable_reflection": false
  }'`,
};

/**
 * Composant de code snippet dynamique avec injection de clé API.
 * 
 * Permet de copier-coller directement du code fonctionnel
 * avec la vraie clé API de l'utilisateur.
 */
export function DynamicCodeSnippet({
  apiKey = "YOUR_API_KEY",
  agentName,
  endpoint = "/api/v1/query",
  baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
}: DynamicCodeSnippetProps) {
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<Language>("python");

  // Masquer la clé si pas visible
  const displayKey = showKey ? apiKey : apiKey.slice(0, 8) + "••••••••";

  // Configurer le code
  const config = {
    apiKey: displayKey,
    baseUrl,
    endpoint,
  };

  const code = CODE_TEMPLATES[activeTab](config);

  // Copier avec la vraie clé
  const handleCopy = useCallback(async () => {
    const realCode = CODE_TEMPLATES[activeTab]({
      ...config,
      apiKey, // Utiliser la vraie clé pour la copie
    });

    await navigator.clipboard.writeText(realCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [activeTab, config, apiKey]);

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Code d'intégration</span>
          {agentName && (
            <Badge variant="outline" className="text-xs">
              {agentName}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle visibilité clé */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowKey(!showKey)}
            className="h-7 px-2 text-xs"
          >
            {showKey ? (
              <>
                <EyeOff className="h-3 w-3 mr-1" />
                Masquer
              </>
            ) : (
              <>
                <Eye className="h-3 w-3 mr-1" />
                Afficher
              </>
            )}
          </Button>

          {/* Bouton copier */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-xs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 mr-1 text-green-500" />
                Copié!
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 mr-1" />
                Copier
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Tabs pour les langages */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Language)}>
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent h-9 p-0">
          <TabsTrigger
            value="python"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            🐍 Python
          </TabsTrigger>
          <TabsTrigger
            value="javascript"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            📦 JavaScript
          </TabsTrigger>
          <TabsTrigger
            value="curl"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            💻 cURL
          </TabsTrigger>
        </TabsList>

        {/* Code blocks */}
        {(["python", "javascript", "curl"] as Language[]).map((lang) => (
          <TabsContent key={lang} value={lang} className="m-0">
            <div className="relative">
              <pre className="p-4 overflow-x-auto text-sm bg-zinc-950 text-zinc-100">
                <code>{CODE_TEMPLATES[lang](config)}</code>
              </pre>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {/* Footer avec avertissement */}
      <div className="px-4 py-2 border-t bg-muted/30 text-xs text-muted-foreground">
        💡 Cliquez sur "Afficher" pour voir votre clé API réelle, puis "Copier" pour l'inclure dans le code.
      </div>
    </div>
  );
}

export default DynamicCodeSnippet;
