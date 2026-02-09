import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
    GraduationCap,
    LayoutDashboard,
    Users,
    School,
    Upload,
    Brain,
    Search,
    RotateCcw,
    Loader2,
} from "lucide-react";
import { useFilters } from "./FilterContext";
import { analyticsApi, ingestionApi } from "@/lib/api";
import type { ReactNode } from "react";
import { useState } from "react";

const navItems = [
    { icon: LayoutDashboard, label: "לוח בקרה", path: "/" },
    { icon: Users, label: "תלמידים", path: "/students" },
    { icon: School, label: "כיתות", path: "/classes" },
    { icon: Upload, label: "טעינת נתונים", path: "/upload" },
    { icon: Brain, label: "תחזיות ML", path: "/predictions" },
];

export function Layout({ children }: { children: ReactNode }) {
    return (
        <div className="flex h-screen overflow-hidden" dir="rtl">
            <Sidebar />
            <main className="flex-1 flex flex-col overflow-y-auto">
                <Header />
                <div className="p-8 space-y-8">{children}</div>
            </main>
        </div>
    );
}

function Sidebar() {
    const routerState = useRouterState();
    const currentPath = routerState.location.pathname;
    const { filters, setFilter } = useFilters();
    const queryClient = useQueryClient();
    const [isResetOpen, setIsResetOpen] = useState(false);

    const { data: metadata } = useQuery({
        queryKey: ["metadata"],
        queryFn: analyticsApi.getMetadata,
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    });

    const resetMutation = useMutation({
        mutationFn: () => ingestionApi.resetDatabase({ reload_data: true }),
        onSuccess: (data) => {
            // Invalidate all queries to refresh data
            queryClient.invalidateQueries();
            setIsResetOpen(false);
            alert(`איפוס בוצע בהצלחה!\nנטענו ${data.students_loaded} תלמידים ו-${data.events_loaded} אירועים`);
        },
        onError: (error) => {
            alert(`שגיאה באיפוס: ${error.message}`);
        },
    });

    return (
        <aside className="w-72 bg-card border-l border-border flex flex-col shrink-0">
            <div className="p-6 flex flex-col gap-6 h-full justify-between">
                <div className="flex flex-col gap-6">
                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="bg-primary/10 rounded-full p-2">
                            <GraduationCap className="size-7 text-primary" />
                        </div>
                        <div className="flex flex-col">
                            <h1 className="text-lg font-bold leading-tight">מבט על שכבתי</h1>
                            <p className="text-muted-foreground text-xs">דשבורד פדגוגי</p>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex flex-col gap-1">
                        {navItems.map((item) => {
                            const isActive = currentPath === item.path ||
                                (item.path !== "/" && currentPath.startsWith(item.path));
                            return (
                                <Link
                                    key={item.path}
                                    to={item.path}
                                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive
                                        ? "bg-primary/10 text-primary"
                                        : "text-muted-foreground hover:bg-accent"
                                        }`}
                                >
                                    <item.icon className="size-5" />
                                    <span className={`text-sm ${isActive ? "font-semibold" : "font-medium"}`}>
                                        {item.label}
                                    </span>
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Filters */}
                    <div className="pt-4 border-t border-border">
                        <p className="text-xs font-bold text-muted-foreground px-3 mb-3 uppercase tracking-wider">
                            סינונים
                        </p>
                        <div className="flex flex-col gap-3 px-1">
                            {/* Period Filter */}
                            <Select
                                value={filters.period || "__all__"}
                                onValueChange={(v) => setFilter("period", v === "__all__" ? undefined : v)}
                            >
                                <SelectTrigger className="h-9 text-sm">
                                    <SelectValue placeholder="כל התקופות" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">כל התקופות</SelectItem>
                                    {metadata?.periods.map((period) => (
                                        <SelectItem key={period} value={period}>
                                            {period}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>

                            {/* Grade Level Filter */}
                            <Select
                                value={filters.gradeLevel || "__all__"}
                                onValueChange={(v) => setFilter("gradeLevel", v === "__all__" ? undefined : v)}
                            >
                                <SelectTrigger className="h-9 text-sm">
                                    <SelectValue placeholder="כל השכבות" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">כל השכבות</SelectItem>
                                    {metadata?.grade_levels.map((level) => (
                                        <SelectItem key={level} value={level}>
                                            שכבה {level}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                {/* Bottom Actions */}
                <div className="flex flex-col gap-3">
                    <Link to="/students">
                        <Button className="w-full gap-2">
                            <Search className="size-4" />
                            <span>חיפוש תלמיד</span>
                        </Button>
                    </Link>

                    {/* Reset Database */}
                    <AlertDialog open={isResetOpen} onOpenChange={setIsResetOpen}>
                        <AlertDialogTrigger asChild>
                            <Button variant="outline" className="w-full gap-2 text-destructive hover:text-destructive">
                                {resetMutation.isPending ? (
                                    <Loader2 className="size-4 animate-spin" />
                                ) : (
                                    <RotateCcw className="size-4" />
                                )}
                                <span>איפוס מסד נתונים</span>
                            </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent dir="rtl">
                            <AlertDialogHeader>
                                <AlertDialogTitle>איפוס מסד הנתונים</AlertDialogTitle>
                                <AlertDialogDescription>
                                    פעולה זו תמחק את כל הנתונים הקיימים ותטען מחדש את הנתונים מקבצי ה-CSV.
                                    האם אתה בטוח שברצונך להמשיך?
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter className="flex-row-reverse gap-2">
                                <AlertDialogCancel>ביטול</AlertDialogCancel>
                                <AlertDialogAction
                                    onClick={() => resetMutation.mutate()}
                                    disabled={resetMutation.isPending}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                    {resetMutation.isPending ? "מאפס..." : "איפוס"}
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </div>
            </div>
        </aside>
    );
}

function Header() {
    return (
        <header className="flex items-center justify-between bg-card border-b border-border px-8 py-4 sticky top-0 z-10">
            <div className="flex items-center gap-6" />
        </header>
    );
}
