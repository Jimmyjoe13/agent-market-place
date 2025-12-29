/**
 * Sidebar de navigation
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  MessageSquare,
  BarChart3,
  Key,
  FileUp,
  Settings,
  Bot,
  Plus,
  Terminal,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const navItems = [
  {
    title: "Chat",
    href: "/chat",
    icon: MessageSquare,
    description: "Discuter avec l'agent",
  },
  {
    title: "Playground",
    href: "/playground",
    icon: Terminal,
    description: "Tester l'API en direct",
    dataTour: "playground-link",
  },
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: BarChart3,
    description: "Statistiques et analytics",
  },
  {
    title: "Documents",
    href: "/documents",
    icon: FileUp,
    description: "Gérer les documents",
  },
  {
    title: "Clés API",
    href: "/keys",
    icon: Key,
    description: "Gérer les clés API",
  },
  {
    title: "Docs",
    href: "/docs",
    icon: BookOpen,
    description: "Documentation API",
    dataTour: "docs-link",
  },
  {
    title: "Paramètres",
    href: "/settings",
    icon: Settings,
    description: "Configuration",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-16 flex-col items-center border-r border-white/10 bg-zinc-950 py-4">
      {/* Logo */}
      <Link
        href="/"
        className="mb-6 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20"
      >
        <Bot className="h-5 w-5 text-white" />
      </Link>

      {/* New Chat Button */}
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <Link href="/chat">
              <Button
                size="icon"
                variant="ghost"
                className="mb-2 h-10 w-10 rounded-xl bg-white/5 hover:bg-white/10"
              >
                <Plus className="h-5 w-5 text-zinc-400" />
              </Button>
            </Link>
          </TooltipTrigger>
          <TooltipContent side="right">Nouvelle conversation</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <Separator className="my-4 w-8 bg-white/10" />

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-2 overflow-y-auto w-full no-scrollbar">
        <TooltipProvider delayDuration={0}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link href={item.href} data-tour={item.dataTour}>
                    <Button
                      size="icon"
                      variant="ghost"
                      className={cn(
                        "h-10 w-10 rounded-xl transition-all",
                        isActive
                          ? "bg-indigo-500/20 text-indigo-400"
                          : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
                      )}
                    >
                      <item.icon className="h-5 w-5" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs text-zinc-400">{item.description}</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </nav>
    </div>
  );
}

export default Sidebar;
