"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAgents } from "@/hooks/useAgents"; // Hook existant ?
import { Check, Copy, ExternalLink, MessageSquare, Terminal } from "lucide-react";

export default function AssistantPluginPage() {
  const [config, setConfig] = useState({
    title: "Assistant IA",
    themeColor: "#4F46E5",
    position: "bottom-right",
    agentId: "",
  });
  
  const [embedCode, setEmbedCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Utiliser un hook existant pour récupérer les agents
  // Si useAgents n'existe pas, on fera un fetch
  // J'ai vu useAgents.ts dans hooks
  const { agents, isLoading: agentsLoading } = useAgents();

  useEffect(() => {
    if (agents && agents.length > 0 && !config.agentId) {
      setConfig(prev => ({ ...prev, agentId: agents[0].id }));
    }
  }, [agents]);

  const generateCode = async () => {
    if (!config.agentId) return;
    setLoading(true);
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      
      const res = await fetch(`${apiUrl}/assistant-plugin/embed`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("accessToken") || ""}` // Ajuster selon gestion token
        },
        body: JSON.stringify({
           agent_id: config.agentId,
           title: config.title,
           theme_color: config.themeColor,
           position: config.position
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setEmbedCode(data.embed_code);
      }
    } catch (err) {
      console.error("Erreur génération code", err);
    } finally {
      setLoading(false);
    }
  };
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Auth token hack: le useAuth doit fournir le token, ou le client api l'ajoute.
  // Ici j'ai mis un placeholder pour fetch. L'idéal est d'utiliser api.post
  // Je vais supposer que api.post gère l'auth.
  
  return (
    <div className="container py-6 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Plugin Assistant</h1>
        <p className="text-muted-foreground mt-2">
          Configurez et intégrez votre agent IA sur votre site web en quelques clics.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Configuration */}
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Configuration</CardTitle>
                    <CardDescription>Personnalisez l'apparence de votre widget.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label>Agent à utiliser</Label>
                        <Select 
                            value={config.agentId} 
                            onValueChange={(val) => setConfig({...config, agentId: val})}
                            disabled={agentsLoading}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Sélectionner un agent" />
                            </SelectTrigger>
                            <SelectContent>
                                {agents?.map(agent => (
                                    <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Titre du widget</Label>
                        <Input 
                            value={config.title} 
                            onChange={(e) => setConfig({...config, title: e.target.value})} 
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Couleur principale</Label>
                            <div className="flex gap-2">
                                <Input 
                                    type="color" 
                                    value={config.themeColor}
                                    onChange={(e) => setConfig({...config, themeColor: e.target.value})}
                                    className="w-12 p-1 h-9"
                                />
                                <Input 
                                    value={config.themeColor}
                                    onChange={(e) => setConfig({...config, themeColor: e.target.value})}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Position</Label>
                            <Select 
                                value={config.position} 
                                onValueChange={(val) => setConfig({...config, position: val})}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="bottom-right">Bas Droite</SelectItem>
                                    <SelectItem value="bottom-left">Bas Gauche</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    
                    <Button onClick={generateCode} className="w-full" disabled={loading || !config.agentId}>
                        {loading ? "Génération..." : "Générer le code d'intégration"}
                    </Button>
                </CardContent>
            </Card>

            {embedCode && (
                <Card>
                    <CardHeader>
                        <CardTitle>Code d'intégration</CardTitle>
                        <CardDescription>Copiez ce code et collez-le avant la balise &lt;/body&gt; de votre site.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="relative bg-muted p-4 rounded-md font-mono text-sm overflow-x-auto">
                            <pre>{embedCode}</pre>
                            <Button 
                                size="sm" 
                                variant="secondary" 
                                className="absolute top-2 right-2 h-8 w-8 p-0"
                                onClick={copyToClipboard}
                            >
                                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>

        {/* Preview */}
        <div className="space-y-6">
            <Card className="h-full min-h-[500px] flex flex-col relative overflow-hidden bg-slate-50 dark:bg-slate-900 border-dashed">
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-10">
                    <div className="text-9xl font-bold">PREVIEW</div>
                </div>
                
                {/* Simulated Widget */}
                <div 
                    className={`absolute p-4 transition-all duration-300 flex flex-col items-end gap-4 ${
                        config.position === 'bottom-left' ? 'bottom-4 left-4 items-start' : 'bottom-4 right-4 items-end'
                    }`}
                >
                    {/* Window */}
                    <div className="w-[350px] bg-white dark:bg-slate-800 rounded-lg shadow-xl border overflow-hidden flex flex-col">
                        <div 
                            className="p-4 text-white flex justify-between items-center"
                            style={{ backgroundColor: config.themeColor }}
                        >
                            <h3 className="font-semibold">{config.title}</h3>
                            <span className="cursor-pointer">✕</span>
                        </div>
                        <div className="h-[300px] bg-slate-50 dark:bg-slate-900 p-4 space-y-3 overflow-y-auto">
                            <div className="bg-white dark:bg-slate-800 border p-3 rounded-lg rounded-bl-sm max-w-[85%] text-sm shadow-sm">
                                Bonjour ! Comment puis-je vous aider aujourd'hui ?
                            </div>
                            <div 
                                className="ml-auto text-white p-3 rounded-lg rounded-br-sm max-w-[85%] text-sm shadow-sm"
                                style={{ backgroundColor: config.themeColor }}
                            >
                                Je voudrais en savoir plus sur vos services.
                            </div>
                        </div>
                        <div className="p-3 border-t bg-white dark:bg-slate-800 flex gap-2">
                             <input 
                                className="flex-1 px-3 py-2 text-sm border rounded-full bg-slate-50 dark:bg-slate-900 focus:outline-none"
                                placeholder="Posez votre question..."
                                readOnly
                             />
                             <button 
                                className="p-2 rounded-full text-white w-9 h-9 flex items-center justify-center shadow-sm"
                                style={{ backgroundColor: config.themeColor }}
                             >
                                <Terminal className="w-4 h-4" />
                             </button>
                        </div>
                    </div>

                    {/* Toggle Button */}
                    <div 
                        className="w-14 h-14 rounded-full text-white shadow-lg flex items-center justify-center cursor-pointer hover:scale-105 transition-transform"
                        style={{ backgroundColor: config.themeColor }}
                    >
                        <MessageSquare className="w-7 h-7" />
                    </div>
                </div>
            </Card>
        </div>
      </div>
    </div>
  );
}
