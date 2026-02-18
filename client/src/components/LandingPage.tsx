import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/auth-store";
import { BarChart3, GraduationCap, LineChart, BrainCircuit, Users, ShieldCheck } from "lucide-react";

export function LandingPage() {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Header */}
            <header className="border-b sticky top-0 z-50 bg-background/80 backdrop-blur-md">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <GraduationCap className="h-6 w-6 text-primary" />
                        <span className="font-bold text-xl">Student Personalizer</span>
                    </div>
                    <nav>
                        {isAuthenticated ? (
                            <Button asChild>
                                <Link to="/dashboard">Go to Dashboard</Link>
                            </Button>
                        ) : (
                            <Button asChild>
                                <Link to="/login">Login</Link>
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
                            Transform Education with <br className="hidden md:block" /> AI-Driven Insights
                        </h1>
                        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                            Empower teachers and administrators with real-time analytics, predictive modeling, and personalized student tracking.
                        </p>
                    </div>
                    <div className="flex gap-4 justify-center animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200">
                        {isAuthenticated ? (
                            <Button size="lg" className="h-12 px-8 text-lg" asChild>
                                <Link to="/dashboard">Enter Dashboard</Link>
                            </Button>
                        ) : (
                            <Button size="lg" className="h-12 px-8 text-lg" asChild>
                                <Link to="/login">Get Started</Link>
                            </Button>
                        )}
                        <Button size="lg" variant="outline" className="h-12 px-8 text-lg pointer-events-none opacity-50">
                            Learn More
                        </Button>
                    </div>
                </section>

                {/* Features Section */}
                <section className="py-20 bg-muted/30">
                    <div className="container mx-auto px-4">
                        <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
                        <div className="grid md:grid-cols-3 gap-8">
                            <FeatureCard
                                icon={<BarChart3 className="h-10 w-10 text-primary" />}
                                title="Advanced Analytics"
                                description="Gain deep insights into class performance, attendance trends, and behavioral patterns with interactive dashboards."
                            />
                            <FeatureCard
                                icon={<BrainCircuit className="h-10 w-10 text-primary" />}
                                title="AI Predictions"
                                description="Leverage machine learning to identify at-risk students early and provide targeted interventions."
                            />
                            <FeatureCard
                                icon={<Users className="h-10 w-10 text-primary" />}
                                title="Student Tracking"
                                description="Monitor individual student progress with detailed profiles and historical data analysis."
                            />
                        </div>
                    </div>
                </section>

                {/* Trust Section */}
                <section className="py-20 px-4">
                    <div className="container mx-auto max-w-5xl">
                        <div className="grid md:grid-cols-2 gap-12 items-center">
                            <div className="space-y-6">
                                <h2 className="text-3xl font-bold">Data-Driven Decision Making</h2>
                                <p className="text-lg text-muted-foreground">
                                    Stop guessing and start knowing. Our platform aggregates data from multiple sources to provide a holistic view of your educational ecosystem.
                                </p>
                                <ul className="space-y-4">
                                    <ListItem text="Real-time data synchronization" />
                                    <ListItem text="Secure and compliant infrastructure" />
                                    <ListItem text="Customizable reporting tools" />
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
                        <span className="font-semibold">Student Personalizer</span>
                    </div>
                    <p>&copy; {new Date().getFullYear()} Student Personalizer. All rights reserved.</p>
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
