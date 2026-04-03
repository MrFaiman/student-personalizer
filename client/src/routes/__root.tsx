import { useEffect, useState } from "react";
import { createRootRoute, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { HelmetProvider } from "react-helmet-async";
import { FilterProvider } from "@/components/FilterContext";
import { Layout } from "@/components/Layout";
import { useConfigStore } from "@/lib/config-store";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api/auth";

function RootComponent() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const currentPath = routerState.location.pathname;

  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated());
  const [sessionBootstrapped, setSessionBootstrapped] = useState(() => {
    if (!useAuthStore.persist.hasHydrated()) return false;
    const s = useAuthStore.getState();
    if (!s.isAuthenticated || !s.user) return true;
    return !!s.accessToken;
  });

  useEffect(() => {
    return useAuthStore.persist.onFinishHydration(() => setHydrated(true));
  }, []);

  useEffect(() => {
    useConfigStore.getState().fetch();
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const run = async () => {
      const s = useAuthStore.getState();
      if (s.isAuthenticated && s.user && !s.accessToken) {
        const ok = await s.refresh();
        if (!ok) {
          useAuthStore.setState({ isAuthenticated: false, user: null });
        }
      }
      setSessionBootstrapped(true);
    };
    void run();
  }, [hydrated]);

  // SSO callback: one-time code in URL fragment
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash.includes("sso_code=")) return;
    const params = new URLSearchParams(hash.slice(1));
    const code = params.get("sso_code");
    if (!code) return;
    void (async () => {
      try {
        const tokens = await authApi.ssoComplete(code);
        const u = await authApi.me(tokens.access_token);
        useAuthStore.setState({
          accessToken: tokens.access_token,
          user: u,
          isAuthenticated: true,
        });
        window.history.replaceState(null, "", window.location.pathname);
        navigate({ to: "/" });
      } catch {
        window.history.replaceState(null, "", window.location.pathname);
        navigate({ to: "/login" });
      }
    })();
  }, [navigate]);

  const onPublicAuthRoute = currentPath === "/login" || currentPath === "/enroll/mfa";
  const sessionReady = !!accessToken && !!user;

  useEffect(() => {
    if (!hydrated || !sessionBootstrapped) return;
    if (onPublicAuthRoute) return;
    if (!sessionReady) {
      navigate({ to: "/login" });
    }
  }, [hydrated, sessionBootstrapped, sessionReady, onPublicAuthRoute, navigate]);

  useEffect(() => {
    const u = useAuthStore.getState().user;
    const enforcedRoles = useConfigStore.getState().mfaEnforcedRoles;
    const isEnforced = u?.role ? enforcedRoles.includes(u.role) : false;
    if (
      sessionReady &&
      isEnforced &&
      !u?.mfa_enabled &&
      currentPath !== "/enroll/mfa" &&
      currentPath !== "/login"
    ) {
      navigate({ to: "/enroll/mfa" });
    }
  }, [sessionReady, currentPath, navigate]);

  if (onPublicAuthRoute) {
    return (
      <HelmetProvider>
        <Outlet />
      </HelmetProvider>
    );
  }

  if (!hydrated || !sessionBootstrapped) {
    return null;
  }

  if (!sessionReady) {
    return null;
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
