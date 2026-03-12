import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/SidebarContent";
import { Header } from "@/components/Header";
import type { ReactNode } from "react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <div className="flex flex-1 flex-col h-svh overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 md:p-8 space-y-4 md:space-y-8">{children}</div>
        </main>
      </div>
    </SidebarProvider>
  );
}
