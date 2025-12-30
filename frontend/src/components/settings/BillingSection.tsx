"use client";

import React, { useState, useEffect } from "react";
import { CreditCard, Zap, Check, ArrowUpRight, BarChart3, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export function BillingSection() {
  const [usage, setUsage] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  const requestPercentage = (usage?.requests_count / usage?.requests_limit) * 100;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-zinc-100">Abonnement & Usage</h3>
          <p className="text-sm text-zinc-400">Gérez votre plan et suivez votre consommation.</p>
        </div>
        <Badge className="bg-indigo-600 text-white border-transparent px-3 py-1">
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
              <Progress value={requestPercentage} className="h-2 bg-zinc-800" />
            </div>
            
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Documents</p>
                <p className="text-sm font-semibold text-zinc-200">12 / 50</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Agents</p>
                <p className="text-sm font-semibold text-zinc-200">2 / 5</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-gradient-to-br from-indigo-600/10 to-transparent bg-zinc-900/50 backdrop-blur-sm border-indigo-500/20">
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-400" /> Passer à Pro
            </CardTitle>
            <CardDescription>Débloquez des limites plus hautes et les modèles premium.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {["Requêtes illimitées", "Support prioritaire", "Modèles GPT-4 & Claude 3", "Accès API précoce"].map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-xs text-zinc-400">
                  <Check className="h-3 w-3 text-green-500" /> {feature}
                </li>
              ))}
            </ul>
            <Button className="w-full bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 group">
              Mettre à niveau <ArrowUpRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-zinc-400" /> Méthode de Paiement
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50 border border-zinc-700/50">
            <div className="flex items-center gap-3">
              <div className="h-8 w-12 bg-zinc-700 rounded flex items-center justify-center text-[10px] font-bold text-zinc-400">VISA</div>
              <div>
                <p className="text-sm font-medium text-zinc-200">•••• •••• •••• 4242</p>
                <p className="text-[10px] text-zinc-500">Expire le 12/26</p>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-zinc-100 text-xs">Modifier</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
