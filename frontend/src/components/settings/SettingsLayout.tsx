"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { User, Key, Cpu, Shield, CreditCard, Activity } from "lucide-react";

interface SettingsLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: "profile", label: "Profil", icon: User },
  { id: "providers", label: "Fournisseurs LLM", icon: Cpu },
  { id: "keys", label: "Clés API RAG", icon: Shield },
  { id: "security", label: "Sécurité & Connexion", icon: Key },
  { id: "billing", label: "Abonnement & Usage", icon: CreditCard },
];

export function SettingsLayout({ children, activeTab, onTabChange }: SettingsLayoutProps) {
  return (
    <div className="flex h-full flex-col md:flex-row overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 border-r border-zinc-800 bg-zinc-900/30 p-4 shrink-0">
        <div className="mb-8 px-2">
          <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
            Paramètres
          </h2>
        </div>
        
        <nav className="space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={cn(
                  "flex w-full items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all",
                  isActive 
                    ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 shadow-[0_0_15px_rgba(79,70,229,0.1)]" 
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50 border border-transparent"
                )}
              >
                <Icon className={cn("h-4 w-4", isActive ? "text-indigo-400" : "text-zinc-500")} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 bg-zinc-950">
        <div className="mx-auto max-w-3xl">
          {children}
        </div>
      </main>
    </div>
  );
}
