"use client";

import React, { useState, useEffect } from "react";
import { CreditCard, Zap, Check, ArrowUpRight, BarChart3, Loader2, Rocket, Settings as SettingsIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export function BillingSection() {
  const [usage, setUsage] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRedirecting, setIsRedirecting] = useState<string | null>(null);

  useEffect(() => {
    async function loadUsage() {
      try {
        const data = await api.getUserUsage();
        setUsage(data);
      } catch (error) {
        toast.error("Impossible de charger les données d'usage");
      } finally {
        setIsLoading(false);
      }
    }
    loadUsage();
  }, []);

  const handleUpgrade = async (plan: "monthly" | "yearly") => {
    setIsRedirecting(plan);
    try {
      const { url } = await api.createCheckoutSession(plan);
      window.location.href = url;
    } catch (error) {
      toast.error("Échec de la création de la session de paiement");
      setIsRedirecting(null);
    }
  };

  const handleManageSubscription = async () => {
    setIsRedirecting("portal");
    try {
      const { url } = await api.createPortalSession();
      window.location.href = url;
    } catch (error) {
      toast.error("Échec de l'accès au portail de gestion");
      setIsRedirecting(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  const isPro = usage?.plan?.toLowerCase() === "pro";
  const requestPercentage = Math.min(100, (usage?.requests_count / usage?.requests_limit) * 100);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-zinc-100">Abonnement & Usage</h3>
          <p className="text-sm text-zinc-400">Gérez votre plan et suivez votre consommation.</p>
        </div>
        <Badge className={`${isPro ? 'bg-indigo-600' : 'bg-zinc-700'} text-white border-transparent px-3 py-1 shadow-lg`}>
          {isPro ? <Rocket className="h-3 w-3 mr-2 inline" /> : null}
          Plan {usage?.plan?.toUpperCase() || "FREE"}
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-400" /> Utilisation Mensuelle
            </CardTitle>
            <CardDescription>Votre quota de requêtes pour la période en cours.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-zinc-400">
                <span>Requêtes API</span>
                <span className="font-medium text-zinc-200">{usage?.requests_count || 0} / {usage?.requests_limit || 100}</span>
              </div>
              <Progress value={requestPercentage} className={`h-2 ${requestPercentage > 90 ? 'bg-red-900/20' : 'bg-zinc-800'}`}>
                <div 
                  className={`h-full transition-all duration-500 ${requestPercentage > 90 ? 'bg-red-500' : 'bg-indigo-500'}`} 
                  style={{ width: `${requestPercentage}%` }} 
                />
              </Progress>
            </div>
            
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Documents</p>
                <p className="text-sm font-semibold text-zinc-200">
                  {usage?.documents_count || 0} / {usage?.documents_limit || 10}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Agents</p>
                <p className="text-sm font-semibold text-zinc-200">
                  {usage?.agents_count || 0} / {usage?.agents_limit || 1}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {isPro ? (
          <Card className="border-indigo-500/20 bg-indigo-500/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Check className="h-4 w-4 text-green-400" /> Abonnement Actif
              </CardTitle>
              <CardDescription>Vous profitez de tous les avantages du Plan Pro.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-zinc-400">
                Votre abonnement sera renouvelé automatiquement. Vous pouvez le gérer ou l'annuler à tout moment.
              </p>
              <Button 
                variant="outline"
                className="w-full border-zinc-700 hover:bg-zinc-800 group"
                onClick={handleManageSubscription}
                disabled={isRedirecting === "portal"}
              >
                {isRedirecting === "portal" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <SettingsIcon className="mr-2 h-4 w-4" />}
                Gérer l'abonnement
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-indigo-500/20 bg-gradient-to-br from-indigo-600/10 to-transparent bg-zinc-900/50 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" /> Passer à Pro
              </CardTitle>
              <CardDescription>Débloquez des limites plus hautes et les modèles premium.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 mb-4">
                {["Requêtes illimitées", "Support prioritaire", "Modèles GPT-4 & Claude 3", "Accès API précoce"].map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-xs text-zinc-400">
                    <Check className="h-3 w-3 text-green-500" /> {feature}
                  </li>
                ))}
              </ul>
              <div className="flex flex-col gap-2">
                <Button 
                  className="w-full bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 group"
                  onClick={() => handleUpgrade("monthly")}
                  disabled={!!isRedirecting}
                >
                  {isRedirecting === "monthly" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Plan Mensuel (19€/m) <ArrowUpRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Button>
                <Button 
                  variant="ghost"
                  className="w-full text-indigo-400 hover:text-indigo-300 text-xs"
                  onClick={() => handleUpgrade("yearly")}
                  disabled={!!isRedirecting}
                >
                  {isRedirecting === "yearly" ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  2 mois offerts avec le plan annuel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-zinc-400" /> Facturation & Historique
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <p className="text-xs text-zinc-500">
              Pour consulter vos factures ou modifier vos informations de paiement, veuillez utiliser le portail sécurisé Stripe.
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              className="w-fit border-zinc-700 text-xs"
              onClick={handleManageSubscription}
              disabled={!isPro || isRedirecting === "portal"}
            >
              Accéder au portail Stripe
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
