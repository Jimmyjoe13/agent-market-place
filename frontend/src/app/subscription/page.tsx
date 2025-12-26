/**
 * Subscription Page (Public)
 * ===========================
 * 
 * Page de tarification publique avec les plans disponibles.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, Sparkles, ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Tarifs | RAG Agent Platform",
  description: "Choisissez le plan adapté à vos besoins. Commencez gratuitement.",
};

export default function SubscriptionPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-lg">RAG Agent</span>
            </Link>
            
            <div className="flex items-center gap-3">
              <Link href="/login">
                <Button variant="ghost" size="sm">Connexion</Button>
              </Link>
              <Link href="/register">
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500">
                  Commencer gratuitement
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="py-20 px-6">
        <div className="mx-auto max-w-5xl">
          {/* Back Link */}
          <Link 
            href="/" 
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-white transition-colors mb-8"
          >
            <ArrowLeft className="h-4 w-4" />
            Retour à l&apos;accueil
          </Link>

          {/* Header */}
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-green-500/10 text-green-400 border-green-500/20">
              Tarifs simples et transparents
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Choisissez votre plan
            </h1>
            <p className="text-zinc-400 max-w-2xl mx-auto text-lg">
              Commencez gratuitement. Évoluez quand vous êtes prêt. 
              Pas de frais cachés, pas d&apos;engagement.
            </p>
          </div>
          
          {/* Pricing Cards */}
          <div className="grid md:grid-cols-3 gap-6">
            {/* Free Plan */}
            <Card className="border-zinc-800 bg-zinc-900/50">
              <CardHeader>
                <CardTitle className="text-xl">Free</CardTitle>
                <CardDescription>Parfait pour découvrir</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold">0€</span>
                  <span className="text-zinc-500">/mois</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3">
                  {[
                    "100 requêtes/mois",
                    "1 clé API",
                    "10 documents",
                    "Support communauté"
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="block">
                  <Button className="w-full" variant="outline">
                    Commencer gratuitement
                  </Button>
                </Link>
              </CardContent>
            </Card>
            
            {/* Pro Plan */}
            <Card className="border-indigo-500/50 bg-zinc-900/50 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge className="bg-indigo-600 text-white">Populaire</Badge>
              </div>
              <CardHeader>
                <CardTitle className="text-xl">Pro</CardTitle>
                <CardDescription>Pour les développeurs sérieux</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold">29€</span>
                  <span className="text-zinc-500">/mois</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3">
                  {[
                    "5 000 requêtes/mois",
                    "5 clés API",
                    "100 documents",
                    "Support email prioritaire",
                    "Playground avancé",
                    "Webhooks"
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="block">
                  <Button className="w-full bg-indigo-600 hover:bg-indigo-500">
                    Commencer l&apos;essai
                  </Button>
                </Link>
              </CardContent>
            </Card>
            
            {/* Scale Plan */}
            <Card className="border-zinc-800 bg-zinc-900/50">
              <CardHeader>
                <CardTitle className="text-xl">Scale</CardTitle>
                <CardDescription>Pour les équipes en croissance</CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold">99€</span>
                  <span className="text-zinc-500">/mois</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3">
                  {[
                    "50 000 requêtes/mois",
                    "Clés API illimitées",
                    "Documents illimités",
                    "Support téléphonique",
                    "Analytics avancés",
                    "SLA 99.9%"
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="block">
                  <Button className="w-full" variant="outline">
                    Contacter les ventes
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>

          {/* FAQ Teaser */}
          <div className="mt-16 text-center">
            <p className="text-zinc-500">
              Des questions ?{" "}
              <a href="mailto:contact@rag-agent.com" className="text-indigo-400 hover:text-indigo-300">
                Contactez-nous
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
