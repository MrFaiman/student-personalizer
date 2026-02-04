import { createFileRoute } from "@tanstack/react-router"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Separator } from "@/components/ui/separator"
import {
  GraduationCap,
  LayoutDashboard,
  TrendingUp,
  TrendingDown,
  Clock,
  Award,
  Users,
  ChevronDown,
  Search,
  FileText,
  Sheet,
  Bell,
  Star,
  CalendarCheck,
  AlertTriangle,
  Plus,
  Minus,
  Eye,
  type LucideIcon,
} from "lucide-react"

export const Route = createFileRoute("/")({
  component: HomePage,
})

const navItems: { icon: LucideIcon; label: string; active: boolean }[] = [
  { icon: LayoutDashboard, label: "לוח בקרה כללי", active: true },
  { icon: TrendingUp, label: "הישגים לימודיים", active: false },
  { icon: Clock, label: "משמעת ונוכחות", active: false },
  { icon: Award, label: "צוות הוראה", active: false },
  { icon: Users, label: "ניהול תלמידים", active: false },
]

const filters = [
  { label: "טווח זמן: סמסטר א'" },
  { label: "שכבה: י'" },
  { label: "מקצוע: הכל" },
  { label: "מורה: הכל" },
]

const kpiData: {
  title: string
  value: string
  change: string
  changeLabel: string
  trend: "up" | "down"
  icon: LucideIcon
  iconColor: string
}[] = [
  {
    title: "ממוצע ציונים שכבתי",
    value: "82.4",
    change: "+2.1%",
    changeLabel: "מהחודש הקודם",
    trend: "up",
    icon: Star,
    iconColor: "text-primary bg-primary/10",
  },
  {
    title: "אחוז נוכחות כללי",
    value: "94.2%",
    change: "-0.5%",
    changeLabel: "מהחודש הקודם",
    trend: "down",
    icon: CalendarCheck,
    iconColor: "text-orange-500 bg-orange-500/10",
  },
  {
    title: "תלמידים בסיכון (מתחת ל-55)",
    value: "14",
    change: "+3",
    changeLabel: "תלמידים חדשים",
    trend: "up",
    icon: AlertTriangle,
    iconColor: "text-red-600 bg-red-600/10",
  },
]

const classGrades = [
  { class: "י-1", grade: 78, height: "75%" },
  { class: "י-2", grade: 92, height: "95%" },
  { class: "י-3", grade: 65, height: "60%" },
  { class: "י-4", grade: 84, height: "85%" },
  { class: "י-5", grade: 72, height: "70%" },
  { class: "י-6", grade: 81, height: "80%" },
]

const urgentStudents = [
  {
    name: "ישראל ישראלי",
    class: "י-2",
    grade: 48,
    attendance: "72%",
    status: "סיכון גבוה",
    statusVariant: "destructive" as const,
  },
  {
    name: "נועה לוי",
    class: "י-1",
    grade: 52,
    attendance: "88%",
    status: "במעקב",
    statusVariant: "secondary" as const,
  },
]

function HomePage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <Header />
        <div className="p-8 space-y-8">
          <KPISection />
          <ChartsSection />
          <StudentsTable />
        </div>
      </main>
    </div>
  )
}

function Sidebar() {
  return (
    <aside className="w-72 bg-card border-l border-border flex flex-col shrink-0">
      <div className="p-6 flex flex-col gap-6 h-full justify-between">
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 rounded-full p-2">
              <GraduationCap className="size-7 text-primary" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-lg font-bold leading-tight">מבט על שכבתי</h1>
              <p className="text-muted-foreground text-xs">דשבורד פדגוגי</p>
            </div>
          </div>

          <nav className="flex flex-col gap-1">
            {navItems.map((item) => (
              <div
                key={item.label}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  item.active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent"
                }`}
              >
                <item.icon className="size-5" />
                <p
                  className={`text-sm ${item.active ? "font-semibold" : "font-medium"}`}
                >
                  {item.label}
                </p>
              </div>
            ))}
          </nav>

          <div className="pt-4 border-t border-border">
            <p className="text-xs font-bold text-muted-foreground px-3 mb-3 uppercase tracking-wider">
              סינונים מהירים
            </p>
            <div className="flex flex-col gap-3 px-1">
              {filters.map((filter) => (
                <button
                  key={filter.label}
                  className="flex items-center justify-between w-full h-9 px-3 rounded-lg bg-accent text-sm"
                >
                  <span className="text-foreground">{filter.label}</span>
                  <ChevronDown className="size-4" />
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <Button className="w-full gap-2">
            <Search className="size-4" />
            <span>חיפוש תלמיד</span>
          </Button>
        </div>
      </div>
    </aside>
  )
}

function Header() {
  return (
    <header className="flex items-center justify-between bg-card border-b border-border px-8 py-4 sticky top-0 z-10">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 text-primary">
            <svg
              fill="currentColor"
              viewBox="0 0 48 48"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                clipRule="evenodd"
                d="M47.2426 24L24 47.2426L0.757355 24L24 0.757355L47.2426 24ZM12.2426 21H35.7574L24 9.24264L12.2426 21Z"
                fillRule="evenodd"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold tracking-tight">Pedagogical BI</h2>
        </div>
        <div className="relative w-72">
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <Search className="size-5 text-muted-foreground" />
          </div>
          <Input
            className="pr-10 bg-accent border-none"
            placeholder="חיפוש מהיר בדשבורד..."
            type="text"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Button className="gap-2">
          <FileText className="size-4" />
          <span>ייצוא PDF</span>
        </Button>
        <Button variant="secondary" className="gap-2">
          <Sheet className="size-4" />
          <span>ייצוא Excel</span>
        </Button>
        <Separator orientation="vertical" className="h-6 mx-2" />
        <Button variant="secondary" size="icon">
          <Bell className="size-5" />
        </Button>
        <Avatar>
          <AvatarImage src="https://lh3.googleusercontent.com/aida-public/AB6AXuCiGannmbarTQn8yT93f-DUMeD_hYgiUIwdZBYRqsOLwBYoTCEhSdfX6iuYuTR2VcyJaBiaMehmGjjno-lfRAMeXZULatgRB5IPVAMrpxS2bKO5nvcopRQJH9IJhBZlLKCPIyzptg_uqi8b-KeTlq3kqA7nuR81ktZyBgEQD4yW1J2dqqGGzy6FpCRnavzaVP6F_EzEdWWrpqdHuTQotSRv005-qg41Fq4GdS7OIMgHL-nL-K-b71Ei_2P4BuwN3_jiMQRN1tkDKgI" />
          <AvatarFallback>U</AvatarFallback>
        </Avatar>
      </div>
    </header>
  )
}

function KPISection() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {kpiData.map((kpi) => (
        <Card key={kpi.title} className="shadow-sm">
          <CardContent className="p-6">
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-start">
                <p className="text-muted-foreground text-sm font-semibold">
                  {kpi.title}
                </p>
                <div className={`${kpi.iconColor} rounded-lg p-1`}>
                  <kpi.icon className="size-5" />
                </div>
              </div>
              <p className="text-3xl font-bold leading-tight">{kpi.value}</p>
              <div className="flex items-center gap-1 mt-1">
                {kpi.trend === "up" ? (
                  <TrendingUp className="size-4 text-green-600" />
                ) : (
                  <TrendingDown className="size-4 text-red-600" />
                )}
                <p
                  className={`text-sm font-semibold ${
                    kpi.trend === "up" ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {kpi.change}
                </p>
                <span className="text-muted-foreground text-xs mr-1">
                  {kpi.changeLabel}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function ChartsSection() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="shadow-sm">
        <CardContent className="p-8">
          <div className="flex flex-col gap-6">
            <div>
              <h3 className="text-lg font-bold">
                השוואת ממוצע ציונים לפי כיתות
              </h3>
              <p className="text-muted-foreground text-sm">
                ספטמבר - ינואר | שכבה י'
              </p>
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-4xl font-bold">82.4</p>
              <p className="text-green-600 text-base font-medium flex items-center">
                <Plus className="size-4" />
                5%
              </p>
            </div>
            <div className="relative h-64 flex items-end justify-between px-4">
              <div className="absolute inset-x-0 bottom-0 h-full border-b border-border flex flex-col justify-between pointer-events-none">
                <div className="w-full border-t border-border opacity-50" />
                <div className="w-full border-t border-border opacity-50" />
                <div className="w-full border-t border-border opacity-50" />
              </div>
              {classGrades.map((item) => (
                <div
                  key={item.class}
                  className="flex flex-col items-center gap-2 w-10 group"
                >
                  <div
                    className="bg-primary/20 hover:bg-primary w-full rounded-t transition-colors duration-300 relative"
                    style={{ height: item.height }}
                  >
                    <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                      {item.grade}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-xs font-bold">
                    {item.class}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardContent className="p-8">
          <div className="flex flex-col gap-6">
            <div>
              <h3 className="text-lg font-bold">מגמת נוכחות שנתית</h3>
              <p className="text-muted-foreground text-sm">
                מבט שנתי - אחוז נוכחות
              </p>
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-4xl font-bold">94.2%</p>
              <p className="text-red-600 text-base font-medium flex items-center">
                <Minus className="size-4" />
                2%
              </p>
            </div>
            <div className="flex flex-col gap-2 mt-4">
              <div className="h-56 w-full relative">
                <svg
                  className="w-full h-full"
                  preserveAspectRatio="none"
                  viewBox="0 0 400 100"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <defs>
                    <linearGradient
                      id="gradient"
                      x1="0%"
                      x2="0%"
                      y1="0%"
                      y2="100%"
                    >
                      <stop
                        offset="0%"
                        stopColor="oklch(0.58 0.17 240)"
                        stopOpacity="0.2"
                      />
                      <stop
                        offset="100%"
                        stopColor="oklch(0.58 0.17 240)"
                        stopOpacity="0"
                      />
                    </linearGradient>
                  </defs>
                  <path
                    d="M0,80 Q50,20 100,50 T200,30 T300,60 T400,20 V100 H0 Z"
                    fill="url(#gradient)"
                  />
                  <path
                    d="M0,80 Q50,20 100,50 T200,30 T300,60 T400,20"
                    fill="none"
                    stroke="oklch(0.58 0.17 240)"
                    strokeLinecap="round"
                    strokeWidth="2"
                  />
                </svg>
              </div>
              <div className="flex justify-between px-2">
                {["ספט", "אוק", "נוב", "דצמ", "ינא"].map((month) => (
                  <p
                    key={month}
                    className="text-muted-foreground text-xs font-bold"
                  >
                    {month}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StudentsTable() {
  return (
    <Card className="shadow-sm overflow-hidden">
      <div className="p-6 border-b border-border flex justify-between items-center">
        <h3 className="text-lg font-bold">תלמידים בטיפול דחוף</h3>
        <Button variant="link" className="text-primary p-0 h-auto">
          צפה בכל התלמידים
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold">שם התלמיד</TableHead>
            <TableHead className="text-right font-bold">כיתה</TableHead>
            <TableHead className="text-right font-bold">ממוצע ציונים</TableHead>
            <TableHead className="text-right font-bold">נוכחות</TableHead>
            <TableHead className="text-right font-bold">סטטוס</TableHead>
            <TableHead className="text-right font-bold">פעולות</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {urgentStudents.map((student) => (
            <TableRow
              key={student.name}
              className="hover:bg-accent/30 transition-colors"
            >
              <TableCell className="font-semibold">{student.name}</TableCell>
              <TableCell>{student.class}</TableCell>
              <TableCell className="font-bold text-red-600">
                {student.grade}
              </TableCell>
              <TableCell>{student.attendance}</TableCell>
              <TableCell>
                <Badge
                  variant={student.statusVariant}
                  className={
                    student.statusVariant === "destructive"
                      ? "bg-red-100 text-red-700 hover:bg-red-100"
                      : "bg-orange-100 text-orange-700 hover:bg-orange-100"
                  }
                >
                  {student.status}
                </Badge>
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-primary hover:text-primary"
                >
                  <Eye className="size-5" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
