/**
 * Playground Code Preview Panel
 * =============================
 * 
 * Affiche l'équivalent de la requête actuelle en cURL, Python ou JavaScript.
 */

"use client";

import { useState } from "react";
import { 
  Code2, 
  Copy, 
  Check, 
  ChevronRight, 
  ChevronDown,
  Globe,
  FileCode,
  Terminal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from "@/components/ui/tabs";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface CodePreviewProps {
  parameters: any;
  requestContent: string;
  agentId?: string | null;
  apiKey?: string;
}

export function CodePreview({ parameters, requestContent, agentId, apiKey }: CodePreviewProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  if (!isExpanded) {
    return (
      <div className="bg-zinc-950 border-t border-white/5 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
          <Code2 className="h-4 w-4 text-emerald-400" />
          Request Preview {agentId && <span className="text-zinc-600">| {agentId.slice(0, 8)}...</span>}
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => setIsExpanded(true)}
          className="h-7 text-xs gap-1"
        >
          View Code <ChevronRight className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Copié dans le presse-papier");
    setTimeout(() => setCopied(false), 2000);
  };

  const keyPlaceholder = apiKey ? `${apiKey.slice(0, 12)}...` : "YOUR_API_KEY";

  const generateCurl = () => {
    return `curl -X POST https://agent-ia-augment.onrender.com/api/v1/query \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${keyPlaceholder}" \\
  -d '{
    "question": "${requestContent.replace(/"/g, '\\"') || "Saisissez votre question..."}",
    "session_id": "optional-session-id",
    "model": "${parameters.model}",
    "system_prompt": "${parameters.systemPrompt?.replace(/"/g, '\\"') || ""}",
    "temperature": ${parameters.temperature},
    "use_rag": ${parameters.rag_enabled !== false ? "true" : "false"},
    "use_web_search": ${parameters.useWebSearch ? "true" : "false"}
  }'`;
  };

  const generatePython = () => {
    return `import requests
import json

url = "https://agent-ia-augment.onrender.com/api/v1/query"
headers = {
    "X-API-Key": "${keyPlaceholder}",
    "Content-Type": "application/json"
}
payload = {
    "question": "${requestContent || "Saisissez votre question..."}",
    "model": "${parameters.model}",
    "system_prompt": "${parameters.systemPrompt?.replace(/"/g, '\\"') || ""}",
    "temperature": ${parameters.temperature},
    "use_rag": ${parameters.rag_enabled !== false ? "True" : "False"},
    "use_web_search": ${parameters.useWebSearch ? "True" : "False"}
}

response = requests.post(url, json=payload, headers=headers)
print(json.dumps(response.json(), indent=2))`;
  };

  const generateJS = () => {
    return `const response = await fetch("https://agent-ia-augment.onrender.com/api/v1/query", {
  method: "POST",
  headers: {
    "X-API-Key": "${keyPlaceholder}",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    question: "${requestContent || "Saisissez votre question..."}",
    model: "${parameters.model}",
    system_prompt: "${parameters.systemPrompt?.replace(/"/g, '\\"') || ""}",
    temperature: ${parameters.temperature},
    use_rag: ${parameters.rag_enabled !== false ? "true" : "false"},
    use_web_search: ${parameters.useWebSearch ? "true" : "false"}
  })
});

const data = await response.json();
console.log(data);`;
  };

  return (
    <div className="bg-zinc-950 border-t border-white/10 flex flex-col h-[350px]">
      <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
          <Code2 className="h-4 w-4 text-emerald-400" />
          API Request Preview
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => setIsExpanded(false)}
          className="h-7 text-xs gap-1"
        >
          Minimiser <ChevronDown className="h-3 w-3" />
        </Button>
      </div>

      <Tabs defaultValue="curl" className="flex-1 flex flex-col">
        <div className="px-4 py-1 bg-zinc-900/50">
          <TabsList className="bg-transparent border-none gap-4">
            <TabsTrigger value="curl" className="data-[state=active]:bg-white/5 data-[state=active]:text-emerald-400 text-zinc-500 text-xs gap-1.5 px-3">
              <Terminal className="h-3 w-3" /> cURL
            </TabsTrigger>
            <TabsTrigger value="python" className="data-[state=active]:bg-white/5 data-[state=active]:text-emerald-400 text-zinc-500 text-xs gap-1.5 px-3">
              <FileCode className="h-3 w-3" /> Python
            </TabsTrigger>
            <TabsTrigger value="js" className="data-[state=active]:bg-white/5 data-[state=active]:text-emerald-400 text-zinc-500 text-xs gap-1.5 px-3">
              <Globe className="h-3 w-3" /> JavaScript
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 relative overflow-auto p-4 group">
          <TabsContent value="curl" className="m-0 font-mono text-xs text-zinc-300 leading-relaxed whitespace-pre">
            {generateCurl()}
          </TabsContent>
          <TabsContent value="python" className="m-0 font-mono text-xs text-zinc-300 leading-relaxed whitespace-pre">
            {generatePython()}
          </TabsContent>
          <TabsContent value="js" className="m-0 font-mono text-xs text-zinc-300 leading-relaxed whitespace-pre">
            {generateJS()}
          </TabsContent>

          <Button 
            size="icon" 
            variant="secondary" 
            className="absolute top-4 right-4 h-8 w-8 bg-zinc-800 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={() => {
              const val = document.querySelector('[data-state="active"].m-0')?.textContent || "";
              copyToClipboard(val);
            }}
          >
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      </Tabs>
    </div>
  );
}
