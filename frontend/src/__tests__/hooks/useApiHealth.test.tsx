/**
 * useApiHealth Hook Tests
 * ========================
 *
 * Tests unitaires pour le hook useApiHealth.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useApiHealth, useApiStatus } from "@/hooks/useApiHealth";
import type { ReactNode } from "react";

// Mock l'API
vi.mock("@/lib/api", () => ({
  api: {
    healthCheck: vi.fn(),
  },
}));

import { api } from "@/lib/api";

// Wrapper avec QueryClient - retry désactivé et pas de refetch
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        refetchInterval: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useApiHealth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns health data when API is healthy", async () => {
    vi.mocked(api.healthCheck).mockResolvedValueOnce({
      status: "healthy",
      version: "1.0.0",
    });

    const { result } = renderHook(() => useApiHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      status: "healthy",
      version: "1.0.0",
    });
  });

  it("handles API errors", async () => {
    vi.mocked(api.healthCheck).mockRejectedValueOnce(new Error("API Error"));

    const { result } = renderHook(() => useApiHealth(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.isError).toBe(true),
      { timeout: 3000 }
    );
  });

  it("respects enabled option", () => {
    const { result } = renderHook(() => useApiHealth({ enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(api.healthCheck).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useApiStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns online when API is healthy", async () => {
    vi.mocked(api.healthCheck).mockResolvedValueOnce({
      status: "healthy",
      version: "1.0.0",
    });

    const { result } = renderHook(() => useApiStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.status).toBe("online"));
    expect(result.current.version).toBe("1.0.0");
  });

  it("returns offline when API is unhealthy", async () => {
    vi.mocked(api.healthCheck).mockResolvedValueOnce({
      status: "unhealthy",
      version: "1.0.0",
    });

    const { result } = renderHook(() => useApiStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.status).toBe("offline"));
  });

  it("returns offline when API call fails", async () => {
    vi.mocked(api.healthCheck).mockRejectedValueOnce(new Error("Network Error"));

    const { result } = renderHook(() => useApiStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => expect(result.current.status).toBe("offline"),
      { timeout: 3000 }
    );
  });

  it("returns loading initially", () => {
    // Create a promise that never resolves
    vi.mocked(api.healthCheck).mockImplementation(
      () => new Promise(() => {})
    );

    const { result } = renderHook(() => useApiStatus(), {
      wrapper: createWrapper(),
    });

    expect(result.current.status).toBe("loading");
    expect(result.current.isLoading).toBe(true);
  });
});
