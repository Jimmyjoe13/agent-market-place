/**
 * Console Layout
 * ==============
 * 
 * Layout pour les pages de la console (Dashboard, Chat, Keys, etc.)
 * Inclut la barre latérale de navigation.
 */

import { Sidebar } from "@/components/sidebar";
import { SectionErrorBoundary } from "@/components/ui/error-boundary";
import OnboardingTour from "@/components/onboarding/OnboardingTour";

export default function ConsoleLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Onboarding Tour (auto-start on first login) */}
      <OnboardingTour />
      
      {/* Sidebar */}
      <SectionErrorBoundary name="Sidebar">
        <Sidebar aria-label="Navigation principale" />
      </SectionErrorBoundary>
      
      {/* Main Content Areas */}
      <main className="flex-1 relative overflow-hidden bg-zinc-950">
        <SectionErrorBoundary name="Content">
          {children}
        </SectionErrorBoundary>
      </main>
    </div>
  );
}
