/**
 * Page de gestion des documents (Ingestion)
 * Utilise sonner pour les notifications toast
 */

"use client";

import { useState, useRef } from "react";
import { FileUp, Github, FileText, Upload, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

type Tab = "text" | "pdf" | "github";

// Configuration des onglets
const TABS = [
  { id: "text" as Tab, label: "Texte", icon: FileText, description: "Collez du texte brut" },
  { id: "pdf" as Tab, label: "PDF", icon: FileUp, description: "Uploadez un fichier PDF" },
  { id: "github" as Tab, label: "GitHub", icon: Github, description: "Importez un repository" },
] as const;

export default function DocumentsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("text");
  const [loading, setLoading] = useState(false);

  // Text ingestion
  const [textContent, setTextContent] = useState("");
  const [textTitle, setTextTitle] = useState("");

  // PDF ingestion
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // GitHub ingestion
  const [githubRepo, setGithubRepo] = useState("");

  // Handler générique pour les erreurs API
  const handleApiError = (error: unknown, defaultMessage: string) => {
    const message = error instanceof Error ? error.message : defaultMessage;
    toast.error("Erreur", {
      description: message,
    });
  };

  const handleTextSubmit = async () => {
    if (!textContent.trim()) {
      toast.warning("Contenu requis", {
        description: "Veuillez entrer du texte à ingérer.",
      });
      return;
    }

    setLoading(true);
    const toastId = toast.loading("Ingestion en cours...", {
      description: "Traitement de votre texte",
    });

    try {
      const response = await api.ingestText({
        content: textContent,
        source_id: `manual:${Date.now()}`,
        title: textTitle || undefined,
      });
      
      toast.success("Texte ingéré avec succès", {
        id: toastId,
        description: response.message || `${textTitle || "Document"} ajouté à la base de connaissances`,
      });
      
      setTextContent("");
      setTextTitle("");
    } catch (error) {
      toast.error("Échec de l'ingestion", {
        id: toastId,
        description: "Impossible d'ingérer le texte. Vérifiez votre connexion.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePdfSubmit = async () => {
    if (!pdfFile) {
      toast.warning("Fichier requis", {
        description: "Veuillez sélectionner un fichier PDF.",
      });
      return;
    }

    setLoading(true);
    const toastId = toast.loading("Upload en cours...", {
      description: `Traitement de ${pdfFile.name}`,
    });

    try {
      const response = await api.ingestPdf(pdfFile);
      
      toast.success("PDF importé avec succès", {
        id: toastId,
        description: response.message || `${pdfFile.name} ajouté à la base de connaissances`,
      });
      
      setPdfFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (error) {
      toast.error("Échec de l'upload", {
        id: toastId,
        description: "Impossible de traiter le PDF. Format invalide ou fichier trop volumineux.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGithubSubmit = async () => {
    if (!githubRepo.trim()) {
      toast.warning("Repository requis", {
        description: "Veuillez entrer un repository GitHub (ex: owner/repo).",
      });
      return;
    }

    // Validation du format
    const repoPattern = /^[\w.-]+\/[\w.-]+$/;
    if (!repoPattern.test(githubRepo.trim())) {
      toast.error("Format invalide", {
        description: "Le format doit être 'owner/repository' (ex: facebook/react)",
      });
      return;
    }

    setLoading(true);
    const toastId = toast.loading("Import GitHub en cours...", {
      description: `Indexation de ${githubRepo}`,
    });

    try {
      const response = await api.ingestGithub({
        repositories: [githubRepo.trim()],
      });
      
      toast.success("Repository importé", {
        id: toastId,
        description: response.message || `${githubRepo} ajouté à la base de connaissances`,
      });
      
      setGithubRepo("");
    } catch (error) {
      toast.error("Échec de l'import GitHub", {
        id: toastId,
        description: "Repository introuvable ou accès refusé. Vérifiez le nom et qu'il est public.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20">
              <Sparkles className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Documents</h1>
              <p className="text-zinc-400">
                Enrichissez votre base de connaissances
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex gap-2">
          {TABS.map((tab) => (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? "default" : "outline"}
              onClick={() => setActiveTab(tab.id)}
              disabled={loading}
              className={
                activeTab === tab.id
                  ? "gap-2 bg-indigo-600 hover:bg-indigo-500"
                  : "gap-2 border-zinc-700 hover:bg-zinc-800"
              }
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </Button>
          ))}
        </div>

        {/* Text Tab */}
        {activeTab === "text" && (
          <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                Ajouter du texte
              </CardTitle>
              <CardDescription>
                Collez du texte brut pour l&apos;ajouter à votre base de connaissances
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                value={textTitle}
                onChange={(e) => setTextTitle(e.target.value)}
                placeholder="Titre (optionnel)"
                className="bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                disabled={loading}
              />
              <Textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Collez votre texte ici..."
                className="min-h-[200px] bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                disabled={loading}
              />
              <div className="flex items-center justify-between">
                <p className="text-xs text-zinc-500">
                  {textContent.length > 0 && `${textContent.length.toLocaleString()} caractères`}
                </p>
                <Button
                  onClick={handleTextSubmit}
                  disabled={!textContent.trim() || loading}
                  className="gap-2 bg-indigo-600 hover:bg-indigo-500"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  Ingérer
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* PDF Tab */}
        {activeTab === "pdf" && (
          <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileUp className="h-5 w-5 text-indigo-400" />
                Upload PDF
              </CardTitle>
              <CardDescription>
                Uploadez un fichier PDF pour extraire et indexer son contenu
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-all ${
                  pdfFile 
                    ? "border-indigo-500/50 bg-indigo-500/5" 
                    : "border-zinc-700 hover:border-indigo-500/50 hover:bg-zinc-800/50"
                } ${loading ? "pointer-events-none opacity-50" : ""}`}
                onClick={() => !loading && fileInputRef.current?.click()}
              >
                <FileUp className={`mx-auto mb-4 h-12 w-12 ${pdfFile ? "text-indigo-400" : "text-zinc-500"}`} />
                {pdfFile ? (
                  <div>
                    <p className="font-medium text-indigo-400">{pdfFile.name}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {(pdfFile.size / 1024 / 1024).toFixed(2)} Mo
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="font-medium text-zinc-300">
                      Cliquez pour sélectionner un PDF
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      ou glissez-déposez votre fichier ici
                    </p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                  disabled={loading}
                />
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handlePdfSubmit}
                  disabled={!pdfFile || loading}
                  className="gap-2 bg-indigo-600 hover:bg-indigo-500"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  Upload et Ingérer
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* GitHub Tab */}
        {activeTab === "github" && (
          <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Github className="h-5 w-5 text-indigo-400" />
                Importer depuis GitHub
              </CardTitle>
              <CardDescription>
                Indexez le code source d&apos;un repository GitHub public
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Input
                  value={githubRepo}
                  onChange={(e) => setGithubRepo(e.target.value)}
                  placeholder="owner/repository (ex: facebook/react)"
                  className="bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                  disabled={loading}
                />
                <p className="text-xs text-zinc-500">
                  Seuls les repositories publics sont supportés
                </p>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleGithubSubmit}
                  disabled={!githubRepo.trim() || loading}
                  className="gap-2 bg-indigo-600 hover:bg-indigo-500"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Github className="h-4 w-4" />}
                  Importer
                </Button>
              </div>
              
              {/* Tips section */}
              <div className="mt-4 rounded-lg bg-zinc-800/50 p-4">
                <p className="text-xs font-medium text-zinc-400 mb-2">💡 Conseils</p>
                <ul className="text-xs text-zinc-500 space-y-1">
                  <li>• Les fichiers README, documentation et code source seront indexés</li>
                  <li>• Les gros repositories peuvent prendre quelques minutes</li>
                  <li>• Vous pouvez indexer plusieurs repositories successivement</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
