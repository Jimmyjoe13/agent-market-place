/**
 * Composant d'onboarding interactif
 * Guide les nouveaux utilisateurs à travers les fonctionnalités principales
 */

'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import type { CallBackProps, Step } from 'react-joyride';

// Import dynamique pour éviter les erreurs SSR
const Joyride = dynamic(() => import('react-joyride'), { ssr: false });

interface OnboardingTourProps {
  /** Forcer le démarrage du tour */
  forceStart?: boolean;
  /** Callback à la fin du tour */
  onComplete?: () => void;
  /** Callback à l'abandon du tour */
  onSkip?: () => void;
}

// Clé localStorage pour tracker si l'onboarding a été fait
const ONBOARDING_KEY = 'rag_onboarding_completed';

// Étapes du tour
const TOUR_STEPS: Step[] = [
  {
    target: 'body',
    placement: 'center',
    title: '🚀 Bienvenue sur RAG Agent IA !',
    content: (
      <div className="space-y-2">
        <p>
          Ce guide rapide va vous montrer comment configurer et utiliser votre agent IA personnel.
        </p>
        <p className="text-sm text-muted-foreground">
          Durée : ~2 minutes
        </p>
      </div>
    ),
    disableBeacon: true,
  },
  {
    target: '[data-tour="api-keys-link"]',
    title: '🔑 Vos Clés API',
    content: (
      <div className="space-y-2">
        <p>
          Chaque clé API représente un <strong>agent</strong> avec sa propre configuration.
        </p>
        <p className="text-sm">
          Créez votre première clé pour commencer !
        </p>
      </div>
    ),
    placement: 'right',
  },
  {
    target: '[data-tour="create-key-btn"]',
    title: '➕ Créer un Agent',
    content: (
      <div className="space-y-2">
        <p>
          Cliquez ici pour créer votre premier agent IA.
        </p>
        <p className="text-sm text-muted-foreground">
          Vous pourrez le configurer ensuite dans le Playground.
        </p>
      </div>
    ),
    placement: 'bottom',
    spotlightClicks: true,
  },
  {
    target: '[data-tour="playground-link"]',
    title: '🎮 Le Playground',
    content: (
      <div className="space-y-2">
        <p>
          C'est ici que vous testez et configurez votre agent.
        </p>
        <ul className="text-sm list-disc list-inside space-y-1">
          <li>Choisir le modèle LLM</li>
          <li>Personnaliser le prompt système</li>
          <li>Activer/désactiver le RAG</li>
        </ul>
      </div>
    ),
    placement: 'right',
  },
  {
    target: '[data-tour="docs-link"]',
    title: '📚 Documentation',
    content: (
      <div className="space-y-2">
        <p>
          Retrouvez ici les exemples de code pour intégrer l'API dans vos applications.
        </p>
        <p className="text-sm text-muted-foreground">
          Python, JavaScript, cURL... tout y est !
        </p>
      </div>
    ),
    placement: 'right',
  },
  {
    target: 'body',
    placement: 'center',
    title: '✨ Vous êtes prêt !',
    content: (
      <div className="space-y-3">
        <p>
          Vous avez les bases pour commencer. N'hésitez pas à explorer !
        </p>
        <div className="p-3 bg-primary/10 rounded-lg">
          <p className="text-sm font-medium">
            💡 Astuce : Commencez par créer une clé API, puis testez-la dans le Playground.
          </p>
        </div>
      </div>
    ),
    disableBeacon: true,
  },
];

// Styles personnalisés pour le tour
const TOUR_STYLES = {
  options: {
    primaryColor: 'hsl(var(--primary))',
    backgroundColor: 'hsl(var(--card))',
    textColor: 'hsl(var(--foreground))',
    arrowColor: 'hsl(var(--card))',
    overlayColor: 'rgba(0, 0, 0, 0.75)',
    zIndex: 10000,
  },
  tooltipContainer: {
    textAlign: 'left' as const,
  },
  tooltipTitle: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: '0.5rem',
  },
  tooltipContent: {
    fontSize: '0.9rem',
    padding: '0.5rem 0',
  },
  buttonNext: {
    backgroundColor: 'hsl(var(--primary))',
    color: 'hsl(var(--primary-foreground))',
    borderRadius: '0.375rem',
    padding: '0.5rem 1rem',
    fontWeight: 500,
  },
  buttonBack: {
    color: 'hsl(var(--muted-foreground))',
    marginRight: '0.5rem',
  },
  buttonSkip: {
    color: 'hsl(var(--muted-foreground))',
  },
  buttonClose: {
    color: 'hsl(var(--muted-foreground))',
  },
};

export default function OnboardingTour({
  forceStart = false,
  onComplete,
  onSkip,
}: OnboardingTourProps) {
  const [run, setRun] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  // Vérifier si l'onboarding doit démarrer
  useEffect(() => {
    if (forceStart) {
      setRun(true);
      return;
    }

    // Démarrer automatiquement si jamais fait
    const hasCompleted = localStorage.getItem(ONBOARDING_KEY);
    if (!hasCompleted) {
      // Petit délai pour laisser la page charger
      const timer = setTimeout(() => setRun(true), 1000);
      return () => clearTimeout(timer);
    }
  }, [forceStart]);

  // Callback pour les événements du tour
  const handleCallback = (data: CallBackProps) => {
    const { status, type, index, action } = data;

    if (type === 'step:after') {
      if (action === 'next') {
        setStepIndex(index + 1);
      } else if (action === 'prev') {
        setStepIndex(index - 1);
      }
    }

    // Tour terminé
    if (status === 'finished') {
      localStorage.setItem(ONBOARDING_KEY, 'true');
      setRun(false);
      onComplete?.();
    }

    // Tour abandonné
    if (status === 'skipped') {
      localStorage.setItem(ONBOARDING_KEY, 'true');
      setRun(false);
      onSkip?.();
    }
  };

  return (
    <Joyride
      steps={TOUR_STEPS}
      run={run}
      stepIndex={stepIndex}
      continuous
      showProgress
      showSkipButton
      scrollToFirstStep
      spotlightPadding={8}
      disableOverlayClose
      locale={{
        back: 'Retour',
        close: 'Fermer',
        last: 'Terminer',
        next: 'Suivant',
        skip: 'Passer',
      }}
      styles={TOUR_STYLES}
      callback={handleCallback}
    />
  );
}

/**
 * Hook pour contrôler l'onboarding manuellement
 */
export function useOnboarding() {
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    const hasCompleted = localStorage.getItem(ONBOARDING_KEY);
    setShouldShow(!hasCompleted);
  }, []);

  const resetOnboarding = () => {
    localStorage.removeItem(ONBOARDING_KEY);
    setShouldShow(true);
  };

  const markComplete = () => {
    localStorage.setItem(ONBOARDING_KEY, 'true');
    setShouldShow(false);
  };

  return {
    shouldShow,
    resetOnboarding,
    markComplete,
  };
}
