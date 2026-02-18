import { useEffect } from "react";
import { createRootRoute, Outlet, useRouterState, Navigate } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { FilterProvider } from "@/components/FilterContext";
import { Layout } from "@/components/Layout";
import { QUERY_STALE_TIME_MS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2 } from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: QUERY_STALE_TIME_MS,
    },
  },
});

function RootComponent() {
  const isInitialized = useAuthStore((s) => s.isInitialized);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    useAuthStore.getState().initialize();
    useConfigStore.getState().fetch();
  }, []);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  const isLoginPage = pathname === "/login";
  const isLandingPage = pathname === "/";

  // Unauthenticated users can only see /login and /
  if (!isAuthenticated && !isLoginPage && !isLandingPage) {
    return (
      <HelmetProvider>
        <QueryClientProvider client={queryClient}>
          <Navigate to="/login" />
        </QueryClientProvider>
      </HelmetProvider>
    );
  }

  if (isLoginPage || isLandingPage) {
    return (
      <HelmetProvider>
        <QueryClientProvider client={queryClient}>
          <Outlet />
        </QueryClientProvider>
      </HelmetProvider>
    );
  }

  return (
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <FilterProvider>
          <Layout>
            <Outlet />
          </Layout>
        </FilterProvider>
      </QueryClientProvider>
    </HelmetProvider>
  );
}

export const Route = createRootRoute({
  component: RootComponent,
});
