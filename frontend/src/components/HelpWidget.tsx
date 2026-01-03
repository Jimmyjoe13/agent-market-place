"use client";

import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// FAQ prédéfinies pour réponses instantanées
const FAQ_RESPONSES: Record<string, string> = {
  "comment créer une clé api": 
    "Pour créer une clé API, allez dans 'Clés API' dans le menu, puis cliquez sur 'Nouvelle clé'. Choisissez un nom et les permissions souhaitées.",
  "comment ajouter un document":
    "Rendez-vous dans 'Documents', cliquez sur 'Ajouter un document', puis uploadez votre fichier PDF ou collez une URL GitHub.",
  "qu'est-ce que le playground":
    "Le Playground vous permet de tester votre agent IA en direct. Posez des questions et voyez les réponses avec les sources utilisées.",
  "comment voir mes statistiques":
    "Le Dashboard affiche toutes vos statistiques : nombre de requêtes, utilisation des tokens, latence moyenne, etc.",
  "tarifs": 
    "Nous proposons un plan gratuit limité et un plan Pro à 29€/mois avec plus de requêtes et fonctionnalités avancées. Voir 'Paramètres' > 'Abonnement'.",
  "contact support":
    "Pour contacter le support, envoyez un email à support@rag-agentia.com ou utilisez ce chat pour les questions fréquentes.",
};

function findFAQAnswer(query: string): string | null {
  const normalizedQuery = query.toLowerCase().trim();
  
  for (const [keyword, answer] of Object.entries(FAQ_RESPONSES)) {
    if (normalizedQuery.includes(keyword) || keyword.includes(normalizedQuery)) {
      return answer;
    }
  }
  return null;
}

export function HelpWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Bonjour ! Je suis l'assistant FAQ. Comment puis-je vous aider ?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    // Simuler un délai de réponse
    await new Promise((resolve) => setTimeout(resolve, 500));

    // Chercher dans les FAQ
    const faqAnswer = findFAQAnswer(userMessage);

    if (faqAnswer) {
      setMessages((prev) => [...prev, { role: "assistant", content: faqAnswer }]);
    } else {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Je n'ai pas trouvé de réponse à votre question dans la FAQ. Voici quelques sujets que je peux vous aider avec :\n\n• Comment créer une clé API\n• Comment ajouter un document\n• Qu'est-ce que le Playground\n• Comment voir mes statistiques\n• Tarifs\n• Contact support",
        },
      ]);
    }

    setIsLoading(false);
  };

  return (
    <>
      {/* Bouton flottant */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-all hover:scale-105",
          isOpen && "scale-0"
        )}
        aria-label="Ouvrir l'aide"
      >
        <MessageCircle className="h-6 w-6" />
      </button>

      {/* Fenêtre de chat */}
      <div
        className={cn(
          "fixed bottom-6 right-6 z-50 flex w-[380px] max-w-[calc(100vw-48px)] flex-col overflow-hidden rounded-2xl border bg-background shadow-2xl transition-all duration-300",
          isOpen ? "h-[500px] opacity-100" : "h-0 opacity-0 pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b bg-primary px-4 py-3 text-primary-foreground">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            <span className="font-semibold">Aide & FAQ</span>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="rounded-full p-1 hover:bg-primary-foreground/20"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
                message.role === "user"
                  ? "ml-auto bg-primary text-primary-foreground rounded-br-sm"
                  : "bg-muted rounded-bl-sm"
              )}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-1.5 px-4 py-2">
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.3s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.15s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50" />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="border-t p-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question..."
              className="flex-1 rounded-full border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isLoading}
            />
            <Button
              type="submit"
              size="icon"
              className="h-10 w-10 rounded-full"
              disabled={isLoading || !input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

export default HelpWidget;
