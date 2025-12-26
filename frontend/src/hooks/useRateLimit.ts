/**
 * Hook pour surveiller le status du rate limiting
 * Permet aux composants de réagir au rate limiting
 */

import { useState, useEffect, useCallback } from "react";
import { getRateLimitInfo, isRateLimited, type RateLimitInfo } from "@/lib/error-handling";

export function useRateLimit() {
  const [info, setInfo] = useState<RateLimitInfo>({
    isRateLimited: false,
    retryAfter: 0,
    retryAt: null,
  });

  const [countdown, setCountdown] = useState(0);

  // Mettre à jour l'état du rate limiting périodiquement
  useEffect(() => {
    const checkRateLimit = () => {
      const currentInfo = getRateLimitInfo();
      setInfo(currentInfo);

      if (currentInfo.isRateLimited && currentInfo.retryAt) {
        const remaining = Math.max(
          0,
          Math.ceil((currentInfo.retryAt.getTime() - Date.now()) / 1000)
        );
        setCountdown(remaining);
      } else {
        setCountdown(0);
      }
    };

    // Vérification initiale
    checkRateLimit();

    // Vérification toutes les secondes
    const interval = setInterval(checkRateLimit, 1000);

    return () => clearInterval(interval);
  }, []);

  // Formater le temps restant
  const formatCountdown = useCallback((seconds: number): string => {
    if (seconds <= 0) return "";
    
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  }, []);

  return {
    isRateLimited: info.isRateLimited,
    retryAfter: info.retryAfter,
    retryAt: info.retryAt,
    countdown,
    formattedCountdown: formatCountdown(countdown),
    canRetry: !info.isRateLimited,
  };
}

export default useRateLimit;
