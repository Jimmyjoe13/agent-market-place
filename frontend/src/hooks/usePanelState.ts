/**
 * Hook pour gérer l'état des panneaux avec persistance localStorage
 * ==================================================================
 * 
 * Permet de sauvegarder l'état collapsed/expanded des panneaux entre sessions.
 * Inclut une gestion SSR-safe (hydration mismatch prevention).
 */

"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "playground_panels_state";

interface PanelState {
  rightCollapsed: boolean;
  codePreviewCollapsed: boolean;
}

const DEFAULT_STATE: PanelState = {
  rightCollapsed: false,
  codePreviewCollapsed: true,
};

/**
 * Hook pour gérer l'état persistant des panneaux du Playground
 * 
 * @returns {Object} État et setters pour chaque panneau
 */
export function usePanelState() {
  // État initialisé à false pour éviter hydration mismatch
  const [isHydrated, setIsHydrated] = useState(false);
  const [state, setState] = useState<PanelState>(DEFAULT_STATE);

  // Hydrater depuis localStorage après le premier render (côté client)
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<PanelState>;
        setState((prev) => ({
          ...prev,
          ...parsed,
        }));
      }
    } catch (error) {
      // localStorage non disponible ou données corrompues
      console.warn("[usePanelState] Failed to read from localStorage:", error);
    }
    setIsHydrated(true);
  }, []);

  // Persister les changements
  useEffect(() => {
    if (!isHydrated) return;
    
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      console.warn("[usePanelState] Failed to write to localStorage:", error);
    }
  }, [state, isHydrated]);

  const toggleRight = useCallback(() => {
    setState((prev) => ({ ...prev, rightCollapsed: !prev.rightCollapsed }));
  }, []);

  const toggleCodePreview = useCallback(() => {
    setState((prev) => ({ ...prev, codePreviewCollapsed: !prev.codePreviewCollapsed }));
  }, []);

  const setRightCollapsed = useCallback((collapsed: boolean) => {
    setState((prev) => ({ ...prev, rightCollapsed: collapsed }));
  }, []);

  const setCodePreviewCollapsed = useCallback((collapsed: boolean) => {
    setState((prev) => ({ ...prev, codePreviewCollapsed: collapsed }));
  }, []);

  return {
    // État
    rightCollapsed: state.rightCollapsed,
    codePreviewCollapsed: state.codePreviewCollapsed,
    isHydrated,
    
    // Toggles
    toggleRight,
    toggleCodePreview,
    
    // Setters directs
    setRightCollapsed,
    setCodePreviewCollapsed,
  };
}

export type { PanelState };
