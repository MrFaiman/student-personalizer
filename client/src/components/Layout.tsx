import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Header } from "@/components/Header";
import { SidebarContent } from "@/components/SidebarContent";
import type { ReactNode } from "react";
import { useState } from "react";

export function Layout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" dir="rtl">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-72 bg-card border-l border-border flex-col shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="right" className="w-72 p-0" showCloseButton={true}>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col overflow-y-auto">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <div className="p-4 md:p-8 space-y-4 md:space-y-8">{children}</div>
      </main>
    </div>
  );
}
