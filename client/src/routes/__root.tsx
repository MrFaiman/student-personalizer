import { useEffect } from "react";
import { createRootRoute, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelmetProvider } from "react-helmet-async";
import { FilterProvider } from "@/components/FilterContext";
import { Layout } from "@/components/Layout";
import { QUERY_STALE_TIME_MS } from "@/lib/constants";
import { useConfigStore } from "@/lib/config-store";
import { useAuthStore } from "@/lib/auth-store";

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
  const navigate = useNavigate();
  const routerState = useRouterState();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const currentPath = routerState.location.pathname;

  useEffect(() => {
    useConfigStore.getState().fetch();
  }, []);

  // SSO callback: parse tokens from URL fragment after OIDC redirect
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes("sso_login=")) {
      const params = new URLSearchParams(hash.slice(1));
      const accessToken = params.get("sso_login");
      const refreshToken = params.get("refresh");
      if (accessToken && refreshToken) {
        const store = useAuthStore.getState();
        store.setTokens(accessToken, refreshToken);
        import("@/lib/api/auth").then(({ authApi }) => {
          authApi.me(accessToken).then((user) => {
            useAuthStore.setState({ user, isAuthenticated: true });
            // Clean the fragment from the URL
            window.history.replaceState(null, "", window.location.pathname);
            navigate({ to: "/" });
          });
        });
      }
    }
  }, [navigate]);

  // Redirect to login if unauthenticated and not already on login page
  useEffect(() => {
    if (!isAuthenticated && currentPath !== "/login") {
      navigate({ to: "/login" });
    }
  }, [isAuthenticated, currentPath, navigate]);

  if (!isAuthenticated && currentPath !== "/login") {
    return null; // Prevent flash of authenticated content
  }

  if (currentPath === "/login") {
    return (
      <HelmetProvider>
        <Outlet />
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
