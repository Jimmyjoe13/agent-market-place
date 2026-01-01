/**
 * Landing Page - RAG Agent Platform
 * ===================================
 * 
 * Page d'accueil SaaS avec Hero, Features, Code Example, Pricing et CTA.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Zap, 
  Shield, 
  Brain, 
  Code2, 
  Sparkles, 
  Globe, 
  Key,
  ArrowRight,
  Check,
  Github,
  Twitter,
  Linkedin
} from "lucide-react";

export const metadata = {
  title: "RAG Agent IA - API d'Intelligence Artificielle Augmentée",
  description: "Intégrez une IA puissante à vos applications. RAG personnalisé avec Mistral AI, recherche web temps réel, et gestion de documents intelligente.",
};

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-950 text-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-lg">RAG Agent</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-zinc-400 hover:text-white transition-colors">Fonctionnalités</a>
              <a href="#api" className="text-sm text-zinc-400 hover:text-white transition-colors">API</a>
              <a href="#pricing" className="text-sm text-zinc-400 hover:text-white transition-colors">Tarifs</a>
              <Link href="/docs" className="text-sm text-zinc-400 hover:text-white transition-colors">Documentation</Link>
            </div>
            
            <div className="flex items-center gap-3">
              <Link href="/login">
                <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white">
                  Connexion
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500">
                  Commencer gratuitement
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
        </div>
        
        <div className="relative mx-auto max-w-5xl text-center">
          <Badge className="mb-6 bg-indigo-500/10 text-indigo-400 border-indigo-500/20 hover:bg-indigo-500/20">
            <Zap className="h-3 w-3 mr-1" />
            Propulsé par Mistral AI + Perplexity
          </Badge>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
              L&apos;IA qui comprend
            </span>
            <br />
            <span className="text-white">vos données</span>
          </h1>
          
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-8 leading-relaxed">
            Intégrez une API de RAG puissante à vos applications. 
            Combinez vos documents, la recherche web et l&apos;IA générative 
            pour des réponses contextuelles uniques.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            <Link href="/register">
              <Button size="lg" className="w-full sm:w-auto gap-2 bg-indigo-600 hover:bg-indigo-500 text-lg px-8">
                Démarrer gratuitement
                <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/docs">
              <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2 border-zinc-700 hover:bg-zinc-800 text-lg px-8">
                <Code2 className="h-5 w-5" />
                Voir la documentation
              </Button>
            </Link>
          </div>
          
          {/* Stats */}
          <div className="flex justify-center gap-12 text-center">
            <div>
              <div className="text-3xl font-bold text-white">100+</div>
              <div className="text-sm text-zinc-500">Requêtes gratuites/mois</div>
            </div>
            <div className="border-l border-zinc-800" />
            <div>
              <div className="text-3xl font-bold text-white">&lt;500ms</div>
              <div className="text-sm text-zinc-500">Temps de réponse moyen</div>
            </div>
            <div className="border-l border-zinc-800" />
            <div>
              <div className="text-3xl font-bold text-white">99.9%</div>
              <div className="text-sm text-zinc-500">Uptime garanti</div>
            </div>
          </div>
        </div>
      </section>

      {/* Code Example Section */}
      <section id="api" className="py-20 px-6 bg-zinc-900/50">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-purple-500/10 text-purple-400 border-purple-500/20">
              <Code2 className="h-3 w-3 mr-1" />
              Simple à intégrer
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Une API, des possibilités infinies
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">
              Intégrez RAG Agent en quelques lignes de code. 
              Compatible avec tous les langages et frameworks.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8 items-center">
            {/* Code Block */}
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur opacity-20" />
              <div className="relative bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  </div>
                  <span className="text-xs text-zinc-500 ml-2">api_example.py</span>
                </div>
                <pre className="p-4 text-sm overflow-x-auto">
                  <code className="text-zinc-300">
{`import requests

response = requests.post(
    "https://api.rag-agent.com/api/v1/query",
    headers={
        "X-API-Key": "sk-proj-votre_cle_ici",
        "Content-Type": "application/json"
    },
    json={
        "question": "Quelles sont mes compétences ?",
        "use_web_search": True
    }
)

# Réponse enrichie avec sources
print(response.json()["answer"])
print(response.json()["sources"])`}
                  </code>
                </pre>
              </div>
            </div>
            
            {/* Features List */}
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <Key className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">Authentification simple</h3>
                  <p className="text-sm text-zinc-400">
                    Clé API unique, gestion des scopes et rate limiting intégré.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <Globe className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">Recherche web temps réel</h3>
                  <p className="text-sm text-zinc-400">
                    Enrichissez vos réponses avec des données actualisées via Perplexity.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                  <Brain className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">RAG personnalisé</h3>
                  <p className="text-sm text-zinc-400">
                    Indexez vos documents (PDF, GitHub, texte) pour des réponses contextuelles.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-20 px-6">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-cyan-500/10 text-cyan-400 border-cyan-500/20">
              <Sparkles className="h-3 w-3 mr-1" />
              Fonctionnalités
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Tout ce dont vous avez besoin
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">
              Une plateforme complète pour intégrer l&apos;IA à vos applications.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: "RAG Intelligent",
                description: "Combine vos documents et le web pour des réponses contextuelles enrichies.",
                color: "indigo",
              },
              {
                icon: Zap,
                title: "Ultra Rapide",
                description: "Temps de réponse < 500ms grâce à Mistral AI et notre infrastructure optimisée.",
                color: "violet",
              },
              {
                icon: Shield,
                title: "Sécurisé",
                description: "Chiffrement SSL, clés API hashées, et isolation des données par tenant.",
                color: "purple",
              },
              {
                icon: Key,
                title: "Self-Service",
                description: "Créez et gérez vos clés API en toute autonomie depuis votre console.",
                color: "cyan",
              },
              {
                icon: Globe,
                title: "Recherche Web",
                description: "Accédez à des informations actualisées via l'intégration Perplexity.",
                color: "green",
              },
              {
                icon: Code2,
                title: "API RESTful",
                description: "Documentation OpenAPI complète, SDKs et exemples pour tous les langages.",
                color: "amber",
              },
            ].map((feature, i) => (
              <Card key={i} className="border-zinc-800 bg-zinc-900/50 hover:border-zinc-700 transition-colors">
                <CardContent className="pt-6">
                  <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-${feature.color}-500/10`}>
                    <feature.icon className={`h-6 w-6 text-${feature.color}-400`} />
                  </div>
                  <h3 className="mb-2 font-semibold text-zinc-100">{feature.title}</h3>
                  <p className="text-sm text-zinc-400">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-6 bg-zinc-900/50">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-green-500/10 text-green-400 border-green-500/20">
              Tarifs transparents
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Commencez gratuitement
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">
              Pas de carte bancaire requise. Passez à un plan supérieur quand vous êtes prêt.
            </p>
          </div>
          
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
                  {["100 requêtes/mois", "1 clé API", "10 documents", "Support communauté"].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400" />
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
                  <span className="text-4xl font-bold">39.99€</span>
                  <span className="text-zinc-500">/mois</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3">
                  {["5 000 requêtes/mois", "5 clés API", "100 documents", "Support email", "Playground avancé"].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400" />
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
                  {["50 000 requêtes/mois", "Clés illimitées", "Documents illimités", "Support prioritaire", "Webhooks & Analytics"].map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-zinc-400">
                      <Check className="h-4 w-4 text-green-400" />
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
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Prêt à intégrer l&apos;IA à vos applications ?
          </h2>
          <p className="text-zinc-400 mb-8 max-w-2xl mx-auto">
            Rejoignez des centaines de développeurs qui utilisent RAG Agent pour créer 
            des expériences IA exceptionnelles.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link href="/register">
              <Button size="lg" className="w-full sm:w-auto gap-2 bg-indigo-600 hover:bg-indigo-500 text-lg px-8">
                Créer un compte gratuit
                <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/playground">
              <Button size="lg" variant="outline" className="w-full sm:w-auto gap-2 border-zinc-700 hover:bg-zinc-800 text-lg px-8">
                Essayer le Playground
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-12 px-6">
        <div className="mx-auto max-w-6xl">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <Link href="/" className="flex items-center gap-2 mb-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <span className="font-bold">RAG Agent</span>
              </Link>
              <p className="text-sm text-zinc-500">
                API d&apos;intelligence artificielle augmentée pour développeurs.
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Produit</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><Link href="/docs" className="hover:text-white transition-colors">Documentation</Link></li>
                <li><Link href="/playground" className="hover:text-white transition-colors">Playground</Link></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Tarifs</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Entreprise</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="#" className="hover:text-white transition-colors">À propos</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Légal</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="/privacy" className="hover:text-white transition-colors">Confidentialité</a></li>
                <li><a href="/terms" className="hover:text-white transition-colors">Conditions</a></li>
              </ul>
            </div>
          </div>
          
          <div className="mt-12 pt-8 border-t border-zinc-800 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-zinc-500">
              © 2024 RAG Agent. Tous droits réservés.
            </p>
            <div className="flex gap-4">
              <a href="#" className="text-zinc-500 hover:text-white transition-colors">
                <Github className="h-5 w-5" />
              </a>
              <a href="#" className="text-zinc-500 hover:text-white transition-colors">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="#" className="text-zinc-500 hover:text-white transition-colors">
                <Linkedin className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
