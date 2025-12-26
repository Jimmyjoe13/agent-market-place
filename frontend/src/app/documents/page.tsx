/**
 * Page de gestion des documents (Ingestion)
 * Utilise React Hook Form + Zod pour la validation
 * et sonner pour les notifications toast
 */

"use client";

import { useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FileUp, Github, FileText, Upload, Loader2, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  textIngestionSchema,
  githubIngestionSchema,
  type TextIngestionFormData,
  type GithubIngestionFormData,
} from "@/lib/validations";

type Tab = "text" | "pdf" | "github";

// Configuration des onglets
const TABS = [
  { id: "text" as Tab, label: "Texte", icon: FileText, description: "Collez du texte brut" },
  { id: "pdf" as Tab, label: "PDF", icon: FileUp, description: "Uploadez un fichier PDF" },
  { id: "github" as Tab, label: "GitHub", icon: Github, description: "Importez un repository" },
] as const;

export default function DocumentsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("text");

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

        {/* Tab Content */}
        {activeTab === "text" && <TextIngestionForm />}
        {activeTab === "pdf" && <PdfIngestionForm />}
        {activeTab === "github" && <GithubIngestionForm />}
      </div>
    </div>
  );
}

// ===== Text Ingestion Form =====

function TextIngestionForm() {
  const form = useForm<TextIngestionFormData>({
    resolver: zodResolver(textIngestionSchema),
    defaultValues: {
      title: "",
      content: "",
    },
  });

  const { isSubmitting } = form.formState;
  const contentValue = form.watch("content");

  async function onSubmit(values: TextIngestionFormData) {
    const toastId = toast.loading("Ingestion en cours...", {
      description: "Traitement de votre texte",
    });

    try {
      const response = await api.ingestText({
        content: values.content,
        source_id: `manual:${Date.now()}`,
        title: values.title || undefined,
      });

      toast.success("Texte ingéré avec succès", {
        id: toastId,
        description: response.message || `${values.title || "Document"} ajouté à la base de connaissances`,
      });

      form.reset();
    } catch (error) {
      toast.error("Échec de l'ingestion", {
        id: toastId,
        description: "Impossible d'ingérer le texte. Vérifiez votre connexion.",
      });
    }
  }

  return (
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
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Titre</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Titre du document (optionnel)"
                      className="bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                      disabled={isSubmitting}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Un titre aide à identifier le document dans les résultats de recherche
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="content"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contenu *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Collez votre texte ici..."
                      className="min-h-[200px] bg-zinc-800 border-zinc-700 focus:border-indigo-500 resize-none"
                      disabled={isSubmitting}
                      {...field}
                    />
                  </FormControl>
                  <div className="flex items-center justify-between">
                    <FormDescription>
                      Minimum 10 caractères
                    </FormDescription>
                    <span className="text-xs text-zinc-500">
                      {contentValue?.length?.toLocaleString() || 0} / 500 000 caractères
                    </span>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="gap-2 bg-indigo-600 hover:bg-indigo-500"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {isSubmitting ? "Ingestion..." : "Ingérer"}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

// ===== PDF Ingestion Form =====

function PdfIngestionForm() {
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (file.size > 50 * 1024 * 1024) {
      return "Le fichier est trop volumineux (max 50 Mo)";
    }
    if (file.type !== "application/pdf") {
      return "Seuls les fichiers PDF sont acceptés";
    }
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        setPdfFile(null);
      } else {
        setError(null);
        setPdfFile(file);
      }
    }
  };

  const handleClearFile = () => {
    setPdfFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async () => {
    if (!pdfFile) {
      setError("Veuillez sélectionner un fichier PDF");
      return;
    }

    setIsSubmitting(true);
    const toastId = toast.loading("Upload en cours...", {
      description: `Traitement de ${pdfFile.name}`,
    });

    try {
      const response = await api.ingestPdf(pdfFile);

      toast.success("PDF importé avec succès", {
        id: toastId,
        description: response.message || `${pdfFile.name} ajouté à la base de connaissances`,
      });

      handleClearFile();
    } catch (error) {
      toast.error("Échec de l'upload", {
        id: toastId,
        description: "Impossible de traiter le PDF. Format invalide ou fichier corrompu.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
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
        <div className="space-y-2">
          <div
            className={`relative cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-all ${
              error
                ? "border-red-500/50 bg-red-500/5"
                : pdfFile
                ? "border-indigo-500/50 bg-indigo-500/5"
                : "border-zinc-700 hover:border-indigo-500/50 hover:bg-zinc-800/50"
            } ${isSubmitting ? "pointer-events-none opacity-50" : ""}`}
            onClick={() => !isSubmitting && fileInputRef.current?.click()}
          >
            <FileUp
              className={`mx-auto mb-4 h-12 w-12 ${
                error ? "text-red-400" : pdfFile ? "text-indigo-400" : "text-zinc-500"
              }`}
            />
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
                  ou glissez-déposez votre fichier ici (max 50 Mo)
                </p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileChange}
              disabled={isSubmitting}
            />

            {/* Clear button */}
            {pdfFile && !isSubmitting && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearFile();
                }}
                className="absolute right-2 top-2 rounded-full p-1 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {error && <p className="text-xs font-medium text-red-400">{error}</p>}
        </div>

        <div className="flex justify-end">
          <Button
            onClick={handleSubmit}
            disabled={!pdfFile || isSubmitting || !!error}
            className="gap-2 bg-indigo-600 hover:bg-indigo-500"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {isSubmitting ? "Upload..." : "Upload et Ingérer"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ===== GitHub Ingestion Form =====

function GithubIngestionForm() {
  const form = useForm<GithubIngestionFormData>({
    resolver: zodResolver(githubIngestionSchema),
    defaultValues: {
      repository: "",
      branch: "",
    },
  });

  const { isSubmitting } = form.formState;

  async function onSubmit(values: GithubIngestionFormData) {
    const toastId = toast.loading("Import GitHub en cours...", {
      description: `Indexation de ${values.repository}`,
    });

    try {
      const response = await api.ingestGithub({
        repositories: [values.repository],
      });

      toast.success("Repository importé", {
        id: toastId,
        description: response.message || `${values.repository} ajouté à la base de connaissances`,
      });

      form.reset();
    } catch (error) {
      toast.error("Échec de l'import GitHub", {
        id: toastId,
        description: "Repository introuvable ou accès refusé. Vérifiez le nom et qu'il est public.",
      });
    }
  }

  return (
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
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="repository"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Repository *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="owner/repository (ex: facebook/react)"
                      className="bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                      disabled={isSubmitting}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Format: propriétaire/nom-du-repo
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="branch"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Branche</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="main (par défaut)"
                      className="bg-zinc-800 border-zinc-700 focus:border-indigo-500"
                      disabled={isSubmitting}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Laissez vide pour utiliser la branche par défaut
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="gap-2 bg-indigo-600 hover:bg-indigo-500"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Github className="h-4 w-4" />
                )}
                {isSubmitting ? "Import..." : "Importer"}
              </Button>
            </div>
          </form>
        </Form>

        {/* Tips section */}
        <div className="mt-6 rounded-lg bg-zinc-800/50 p-4">
          <p className="text-xs font-medium text-zinc-400 mb-2">💡 Conseils</p>
          <ul className="text-xs text-zinc-500 space-y-1">
            <li>• Les fichiers README, documentation et code source seront indexés</li>
            <li>• Les gros repositories peuvent prendre quelques minutes</li>
            <li>• Seuls les repositories publics sont supportés</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
