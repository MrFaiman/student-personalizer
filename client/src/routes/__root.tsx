import { useEffect } from "react";
import { createRootRoute, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { HelmetProvider } from "react-helmet-async";
import { FilterProvider } from "@/components/FilterContext";
import { Layout } from "@/components/Layout";
import { useConfigStore } from "@/lib/config-store";
import { useAuthStore } from "@/lib/auth-store";

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

  // Enforce MFA enrollment for admin accounts
  useEffect(() => {
    const { user } = useAuthStore.getState();
    const enforcedRoles = useConfigStore.getState().mfaEnforcedRoles;
    const isEnforced = user?.role ? enforcedRoles.includes(user.role) : false;
    if (
      isAuthenticated &&
      isEnforced &&
      !user?.mfa_enabled &&
      currentPath !== "/enroll/mfa" &&
      currentPath !== "/login"
    ) {
      navigate({ to: "/enroll/mfa" });
    }
  }, [isAuthenticated, currentPath, navigate]);

  if (!isAuthenticated && currentPath !== "/login") {
    return null; // Prevent flash of authenticated content
  }

  if (currentPath === "/login" || currentPath === "/enroll/mfa") {
    return (
      <HelmetProvider>
        <Outlet />
      </HelmetProvider>
    );
  }

  return (
    <HelmetProvider>
      <FilterProvider>
        <Layout>
          <Outlet />
        </Layout>
      </FilterProvider>
    </HelmetProvider>
  );
}

export const Route = createRootRoute({
  component: RootComponent,
});
