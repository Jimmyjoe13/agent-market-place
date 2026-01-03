/**
 * Console Layout (Responsive)
 * ===========================
 * 
 * Layout pour les pages de la console (Dashboard, Chat, Keys, etc.)
 * 
 * - Desktop (md+) : Sidebar fixe à gauche
 * - Mobile : Bouton menu flottant + Drawer
 */

import { Sidebar } from "@/components/sidebar";
import { SectionErrorBoundary } from "@/components/ui/error-boundary";
import OnboardingTour from "@/components/onboarding/OnboardingTour";
import HelpWidget from "@/components/HelpWidget";

export default function ConsoleLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Onboarding Tour (auto-start on first login) */}
      <OnboardingTour />
      
      {/* Sidebar - Desktop: fixed | Mobile: Drawer via Sheet */}
      <SectionErrorBoundary name="Sidebar">
        <Sidebar aria-label="Navigation principale" />
      </SectionErrorBoundary>
      
      {/* Main Content Areas */}
      <main className="flex-1 relative overflow-hidden">
        {/* 
          Mobile: padding-top pour éviter le chevauchement avec le bouton menu flottant
          Le bouton est positionné à top-3 (12px) avec une hauteur de 40px
        */}
        <div className="h-full md:pt-0 pt-14">
          <SectionErrorBoundary name="Content">
            {children}
          </SectionErrorBoundary>
        </div>
      </main>
      
      {/* Help Widget - FAQ Chatbot flottant */}
      <HelpWidget />
    </div>
  );
}
