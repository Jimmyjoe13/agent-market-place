/**
 * Coming Soon Component
 * ======================
 * 
 * Affiche un état "Coming Soon" pour les fonctionnalités en cours de développement.
 */

"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Construction, ArrowLeft, Bell } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface ComingSoonProps {
  title: string;
  description?: string;
  expectedDate?: string;
}

export function ComingSoon({ 
  title, 
  description = "Cette fonctionnalité est en cours de développement.",
  expectedDate 
}: ComingSoonProps) {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleNotify = () => {
    if (!email) return;
    // Simuler inscription newsletter
    setSubscribed(true);
    toast.success("Inscription réussie", {
      description: "Vous serez notifié dès que cette fonctionnalité sera disponible.",
    });
  };

  return (
    <div className="flex h-full items-center justify-center p-8">
      <Card className="max-w-md w-full border-zinc-800 bg-zinc-900/50">
        <CardContent className="pt-8 text-center">
          {/* Icon */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10">
            <Construction className="h-8 w-8 text-amber-400" />
          </div>
          
          {/* Title */}
          <h1 className="text-2xl font-bold text-white mb-2">{title}</h1>
          <p className="text-zinc-400 mb-6">{description}</p>
          
          {expectedDate && (
            <p className="text-sm text-zinc-500 mb-6">
              Disponibilité prévue : <span className="text-indigo-400">{expectedDate}</span>
            </p>
          )}
          
          {/* Notify Form */}
          {!subscribed ? (
            <div className="space-y-3">
              <p className="text-sm text-zinc-500">
                Soyez notifié dès que c&apos;est prêt
              </p>
              <div className="flex gap-2">
                <input
                  type="email"
                  placeholder="votre@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <Button onClick={handleNotify} className="bg-indigo-600 hover:bg-indigo-500">
                  <Bell className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
              ✓ Vous serez notifié par email
            </div>
          )}
          
          {/* Back Link */}
          <div className="mt-8">
            <Link href="/dashboard">
              <Button variant="ghost" className="gap-2 text-zinc-400">
                <ArrowLeft className="h-4 w-4" />
                Retour au dashboard
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default ComingSoon;
