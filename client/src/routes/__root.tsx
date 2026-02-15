import { useEffect } from "react";
import { createRootRoute, Outlet } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { FilterProvider } from "@/components/FilterContext";
import { Layout } from "@/components/Layout";
import { QUERY_STALE_TIME_MS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";

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
  useEffect(() => {
    useConfigStore.getState().fetch();
  }, []);

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
