/**
 * Sidebar de navigation (Responsive)
 * ===================================
 * 
 * Desktop : Barre latérale fixe avec icônes
 * Mobile : Drawer escamotable via Sheet
 */

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  Key,
  FileUp,
  Settings,
  Bot,
  Plus,
  Terminal,
  BookOpen,
  Menu,
  X,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

const navItems = [
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
    dataTour: "api-keys-link",
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

interface NavItemProps {
  item: typeof navItems[0];
  isActive: boolean;
  showLabel?: boolean;
  onClick?: () => void;
}

function NavItem({ item, isActive, showLabel = false, onClick }: NavItemProps) {
  return (
    <Link 
      href={item.href} 
      data-tour={item.dataTour}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all",
        showLabel ? "w-full" : "h-10 w-10 justify-center",
        isActive
          ? "bg-primary/15 text-primary"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
    >
      <item.icon className="h-5 w-5 shrink-0" />
      {showLabel && (
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{item.title}</p>
          <p className="text-xs text-muted-foreground truncate">{item.description}</p>
        </div>
      )}
    </Link>
  );
}

/**
 * Version Desktop de la sidebar (icônes uniquement)
 */
function DesktopSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    await signOut();
    // La redirection est gérée automatiquement par useAuth
  };

  return (
    <div className="hidden md:flex h-full w-16 flex-col items-center border-r border-border bg-sidebar py-4">
      {/* Logo */}
      <Link
        href="/"
        className="mb-6 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-brand shadow-lg glow-brand"
      >
        <Bot className="h-5 w-5 text-primary-foreground" />
      </Link>

      {/* New Chat Button */}
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <Link href="/chat">
              <Button
                size="icon"
                variant="ghost"
                className="mb-2 h-10 w-10 rounded-xl bg-accent/50 hover:bg-accent"
              >
                <Plus className="h-5 w-5 text-muted-foreground" />
              </Button>
            </Link>
          </TooltipTrigger>
          <TooltipContent side="right">Nouvelle conversation</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <Separator className="my-4 w-8 bg-border" />

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-2 overflow-y-auto w-full no-scrollbar">
        <TooltipProvider delayDuration={0}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <div>
                    <NavItem item={item} isActive={isActive} />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </nav>

      {/* Logout Button */}
      <Separator className="my-4 w-8 bg-border" />
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="h-10 w-10 rounded-xl text-muted-foreground hover:bg-red-500/10 hover:text-red-500"
              onClick={handleSignOut}
            >
              <LogOut className="h-5 w-5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p className="font-medium">Déconnexion</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

/**
 * Version Mobile de la sidebar (Drawer)
 */
function MobileSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { signOut } = useAuth();
  const [open, setOpen] = useState(false);

  const handleNavClick = () => {
    setOpen(false);
  };

  const handleSignOut = async () => {
    setOpen(false);
    await signOut();
    // La redirection est gérée automatiquement par useAuth
  };

  return (
    <div className="md:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="fixed top-3 left-3 z-40 h-10 w-10 rounded-xl bg-background/80 backdrop-blur-sm border border-border shadow-lg"
            aria-label="Ouvrir le menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        
        <SheetContent side="left" className="w-72 p-0 bg-sidebar flex flex-col" showCloseButton={false}>
          <SheetHeader className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <Link
                href="/"
                className="flex items-center gap-3"
                onClick={handleNavClick}
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-brand shadow-lg">
                  <Bot className="h-5 w-5 text-primary-foreground" />
                </div>
                <SheetTitle className="text-lg font-bold">RAG Agent</SheetTitle>
              </Link>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </SheetHeader>

          {/* New Chat */}
          <div className="p-4 border-b border-border">
            <Link href="/chat" onClick={handleNavClick}>
              <Button className="w-full gap-2 bg-primary hover:bg-primary/90">
                <Plus className="h-4 w-4" />
                Nouvelle conversation
              </Button>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <NavItem
                  key={item.href}
                  item={item}
                  isActive={isActive}
                  showLabel
                  onClick={handleNavClick}
                />
              );
            })}
          </nav>

          {/* Footer with Logout */}
          <div className="p-4 border-t border-border space-y-3">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-muted-foreground hover:bg-red-500/10 hover:text-red-500"
              onClick={handleSignOut}
            >
              <LogOut className="h-5 w-5" />
              Déconnexion
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              © 2024 RAG Agent. v0.1.0
            </p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

/**
 * Sidebar composite : affiche Desktop ou Mobile selon le viewport
 */
export function Sidebar() {
  return (
    <>
      <DesktopSidebar />
      <MobileSidebar />
    </>
  );
}

export default Sidebar;
