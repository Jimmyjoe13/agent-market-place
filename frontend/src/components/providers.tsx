/**
 * Providers pour l'application (React Query, Theme, Notifications)
 * 
 * Note: Supabase Auth n'a pas besoin de provider, la session est gérée via cookies.
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useState } from "react";

import { SyncSession } from "@/components/auth/sync-session";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <SyncSession />
      {children}
      <Toaster
        position="top-right"
        expand={false}
        richColors
        closeButton
        theme="dark"
        toastOptions={{
          style: {
            background: "hsl(240 10% 10%)",
            border: "1px solid hsl(240 5% 20%)",
            color: "hsl(0 0% 95%)",
          },
          classNames: {
            success: "!bg-green-950/90 !border-green-800/50",
            error: "!bg-red-950/90 !border-red-800/50",
            warning: "!bg-amber-950/90 !border-amber-800/50",
            info: "!bg-indigo-950/90 !border-indigo-800/50",
          },
        }}
      />
    </QueryClientProvider>
  );
}

export default Providers;
