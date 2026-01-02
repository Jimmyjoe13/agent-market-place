/**
 * AnimatedCounter Component
 * =========================
 * 
 * Affiche un nombre avec une animation fluide lors des changements.
 * Utilise CSS transitions pour un effet premium.
 */

"use client";

import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  className?: string;
  formatFn?: (value: number) => string;
}

export function AnimatedCounter({
  value,
  duration = 500,
  className,
  formatFn = (v) => v.toLocaleString(),
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(value);
  const [isAnimating, setIsAnimating] = useState(false);
  const previousValueRef = useRef(value);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const previousValue = previousValueRef.current;
    
    // Si la valeur n'a pas changé, ne rien faire
    if (previousValue === value) return;
    
    previousValueRef.current = value;
    setIsAnimating(true);
    
    const startTime = performance.now();
    const startValue = displayValue;
    const diff = value - startValue;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function (ease-out-cubic)
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentValue = Math.round(startValue + diff * easeProgress);
      setDisplayValue(currentValue);
      
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(value);
        setIsAnimating(false);
      }
    };
    
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value, duration, displayValue]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <span
      className={cn(
        "tabular-nums transition-colors duration-200",
        isAnimating && "text-primary",
        className
      )}
    >
      {formatFn(displayValue)}
    </span>
  );
}

/**
 * Variante compacte avec flash highlight
 */
interface FlashCounterProps extends AnimatedCounterProps {
  highlightOnChange?: boolean;
}

export function FlashCounter({
  value,
  className,
  formatFn = (v) => v.toLocaleString(),
  highlightOnChange = true,
}: FlashCounterProps) {
  const [isHighlighted, setIsHighlighted] = useState(false);
  const previousValueRef = useRef(value);

  useEffect(() => {
    if (previousValueRef.current !== value && highlightOnChange) {
      setIsHighlighted(true);
      previousValueRef.current = value;
      
      const timeout = setTimeout(() => {
        setIsHighlighted(false);
      }, 600);
      
      return () => clearTimeout(timeout);
    }
  }, [value, highlightOnChange]);

  return (
    <span
      className={cn(
        "tabular-nums transition-all duration-300",
        isHighlighted && "text-primary scale-110",
        className
      )}
    >
      {formatFn(value)}
    </span>
  );
}

export default AnimatedCounter;
