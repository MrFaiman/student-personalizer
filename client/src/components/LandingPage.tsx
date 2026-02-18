import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { BarChart3, GraduationCap, LineChart, BrainCircuit, Users, ShieldCheck } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";

export function LandingPage() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    const { t } = useTranslation("landing");

    return (
        <div className="min-h-screen bg-background flex flex-col" dir="rtl">
            {/* Header */}
            <header className="border-b sticky top-0 z-50 bg-background/80 backdrop-blur-md">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <GraduationCap className="h-6 w-6 text-primary" />
                        <span className="font-bold text-xl">{t("appName", { ns: "common" })}</span>
                    </div>
                    <nav>
                        {isAuthenticated ? (
                            <Button asChild>
                                <Link to="/dashboard">{t("hero.cta.dashboard")}</Link>
                            </Button>
                        ) : (
                            <Button asChild>
                                <Link to="/login">{t("hero.cta.login")}</Link>
                            </Button>
                        )}
                    </nav>
                </div>
            </header>

            {/* Hero Section */}
            <main className="flex-1 bg-background select-none">
                <section className="py-20 md:py-32 px-4 text-center space-y-8 max-w-4xl mx-auto">
                    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
                        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-foreground bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
                            <Trans i18nKey="hero.title" ns="landing" components={{ br: <br className="hidden md:block" /> }} />
                        </h1>
                        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                            {t("hero.subtitle")}
                        </p>
                    </div>
                    <div className="flex gap-4 justify-center animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200">
                        {isAuthenticated ? (
                            <Button size="lg" className="h-12 px-8 text-lg" asChild>
                                <Link to="/dashboard">{t("hero.cta.dashboard")}</Link>
                            </Button>
                        ) : (
                            <Button size="lg" className="h-12 px-8 text-lg" asChild>
                                <Link to="/login">{t("hero.cta.getStarted")}</Link>
                            </Button>
                        )}
                        <Button size="lg" variant="outline" className="h-12 px-8 text-lg pointer-events-none opacity-50">
                            {t("hero.cta.learnMore")}
                        </Button>
                    </div>
                </section>

                {/* Features Section */}
                <section className="py-20 bg-muted/30">
                    <div className="container mx-auto px-4">
                        <h2 className="text-3xl font-bold text-center mb-12">{t("features.title")}</h2>
                        <div className="grid md:grid-cols-3 gap-8">
                            <FeatureCard
                                icon={<BarChart3 className="h-10 w-10 text-primary" />}
                                title={t("features.analytics.title")}
                                description={t("features.analytics.description")}
                            />
                            <FeatureCard
                                icon={<BrainCircuit className="h-10 w-10 text-primary" />}
                                title={t("features.predictions.title")}
                                description={t("features.predictions.description")}
                            />
                            <FeatureCard
                                icon={<Users className="h-10 w-10 text-primary" />}
                                title={t("features.tracking.title")}
                                description={t("features.tracking.description")}
                            />
                        </div>
                    </div>
                </section>

                {/* Trust Section */}
                <section className="py-20 px-4">
                    <div className="container mx-auto max-w-5xl">
                        <div className="grid md:grid-cols-2 gap-12 items-center">
                            <div className="space-y-6">
                                <h2 className="text-3xl font-bold">{t("trust.title")}</h2>
                                <p className="text-lg text-muted-foreground">
                                    {t("trust.description")}
                                </p>
                                <ul className="space-y-4">
                                    <ListItem text={t("trust.list.sync")} />
                                    <ListItem text={t("trust.list.secure")} />
                                    <ListItem text={t("trust.list.reporting")} />
                                </ul>
                            </div>
                            <div className="bg-muted p-8 rounded-2xl aspect-video flex items-center justify-center relative overflow-hidden group">
                                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-blue-500/10 opacity-50 group-hover:opacity-100 transition-opacity" />
                                <LineChart className="w-32 h-32 text-primary/40 group-hover:scale-110 transition-transform duration-500" />
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="border-t py-12 bg-muted/20">
                <div className="container mx-auto px-4 text-center text-muted-foreground">
                    <div className="flex justify-center items-center gap-2 mb-4">
                        <GraduationCap className="h-5 w-5" />
                        <span className="font-semibold">{t("appName", { ns: "common" })}</span>
                    </div>
                    <p>&copy; {new Date().getFullYear()} {t("appName", { ns: "common" })}. {t("footer.rights")}</p>
                </div>
            </footer>
        </div>
    );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="bg-card p-6 rounded-xl border shadow-sm hover:shadow-md transition-shadow">
            <div className="mb-4 bg-primary/10 w-16 h-16 rounded-lg flex items-center justify-center">
                {icon}
            </div>
            <h3 className="text-xl font-bold mb-2">{title}</h3>
            <p className="text-muted-foreground">{description}</p>
        </div>
    );
}

function ListItem({ text }: { text: string }) {
    return (
        <li className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-green-500" />
            <span>{text}</span>
        </li>
    )
}
