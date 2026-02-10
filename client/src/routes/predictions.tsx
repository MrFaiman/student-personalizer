import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Brain,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingDown,
  Clock,
  Users,
  Eye,
} from "lucide-react";
import { useState } from "react";
import { useFilters } from "@/components/FilterContext";
import { TablePagination } from "@/components/TablePagination";
import { mlApi } from "@/lib/api";

export const Route = createFileRoute("/predictions")({
  component: PredictionsPage,
});

function PredictionsPage() {
  const queryClient = useQueryClient();
  const { filters } = useFilters();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Reset page to 1 when global filters change
  const [prevPeriod, setPrevPeriod] = useState(filters.period);
  if (prevPeriod !== filters.period) {
    setPrevPeriod(filters.period);
    setPage(1);
  }

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["ml-status"],
    queryFn: mlApi.getStatus,
  });

  const { data: predictions, isLoading: predictionsLoading } = useQuery({
    queryKey: ["ml-predictions", filters.period, page],
    queryFn: () => mlApi.predictAll({ period: filters.period, page, page_size: pageSize }),
    enabled: !!status?.trained,
    placeholderData: keepPreviousData,
  });

  const trainMutation = useMutation({
    mutationFn: () => mlApi.train({ period: filters.period }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ml-status"] });
      queryClient.invalidateQueries({ queryKey: ["ml-predictions"] });
    },
  });

  const getRiskBadge = (riskLevel: string) => {
    switch (riskLevel) {
      case "high":
        return <Badge className="bg-red-100 text-red-700">סיכון גבוה</Badge>;
      case "medium":
        return <Badge className="bg-yellow-100 text-yellow-700">סיכון בינוני</Badge>;
      default:
        return <Badge className="bg-green-100 text-green-700">סיכון נמוך</Badge>;
    }
  };

  const totalPredictions = predictions?.total || 0;
  const highRiskCount = predictions?.high_risk_count ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">תחזיות ML</h1>
        <p className="text-muted-foreground">
          חיזוי ציונים וזיהוי תלמידים בסיכון נשירה באמצעות למידת מכונה
        </p>
      </div>

      {/* Model Status Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div
                className={`rounded-lg p-3 ${status?.trained ? "bg-green-100" : "bg-yellow-100"
                  }`}
              >
                <Brain
                  className={`size-8 ${status?.trained ? "text-green-600" : "text-yellow-600"}`}
                />
              </div>
              <div>
                <h3 className="text-lg font-bold">סטטוס המודל</h3>
                {statusLoading ? (
                  <Skeleton className="h-5 w-32 mt-1" />
                ) : status?.trained ? (
                  <div className="flex items-center gap-2 text-green-600 mt-1">
                    <CheckCircle className="size-4" />
                    <span>המודל מאומן ומוכן לשימוש</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-yellow-600 mt-1">
                    <AlertTriangle className="size-4" />
                    <span>המודל לא אומן עדיין</span>
                  </div>
                )}
              </div>
            </div>
            <Button
              onClick={() => trainMutation.mutate()}
              disabled={trainMutation.isPending}
              className="gap-2"
            >
              <RefreshCw className={`size-4 ${trainMutation.isPending ? "animate-spin" : ""}`} />
              {trainMutation.isPending ? "מאמן..." : "אמן מודל"}
            </Button>
          </div>

          {!statusLoading && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t">
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums">{status?.samples ?? "—"}</div>
                <div className="text-sm text-muted-foreground">דגימות באימון</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums">
                  {status?.grade_model_mae != null ? status.grade_model_mae.toFixed(2) : "—"}
                </div>
                <div className="text-sm text-muted-foreground">MAE ציונים</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold tabular-nums">
                  {status?.dropout_model_accuracy != null
                    ? `${(status.dropout_model_accuracy * 100).toFixed(1)}%`
                    : "—"}
                </div>
                <div className="text-sm text-muted-foreground">דיוק נשירה</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {status?.trained_at
                    ? new Date(status.trained_at).toLocaleString("he-IL")
                    : "—"}
                </div>
                <div className="text-sm text-muted-foreground">תאריך אימון אחרון</div>
              </div>
            </div>
          )}

          {trainMutation.isSuccess && (
            <div className="mt-4 p-3 bg-green-100 rounded-lg flex items-center gap-2 text-green-800">
              <CheckCircle className="size-5" />
              <span>
                המודל אומן בהצלחה על {trainMutation.data.samples_used} דגימות
              </span>
            </div>
          )}

          {trainMutation.isError && (
            <div className="mt-4 p-3 bg-red-100 rounded-lg flex items-center gap-2 text-red-800">
              <XCircle className="size-5" />
              <span>{(trainMutation.error as Error).message}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Cards */}
      {status?.trained && predictions && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-primary/10 rounded-lg p-2">
                <Users className="size-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold tabular-nums">{totalPredictions}</p>
                <p className="text-sm text-muted-foreground">תלמידים בתחזית</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-4">
              <div className="bg-red-100 rounded-lg p-2">
                <AlertTriangle className="size-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600 tabular-nums">{highRiskCount}</p>
                <p className="text-sm text-muted-foreground">סיכון גבוה לנשירה</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Predictions Table */}
      {status?.trained && (
        <Card>
          <div className="p-6 border-b">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <TrendingDown className="size-5 text-muted-foreground" />
              תחזיות לכל התלמידים
            </h3>
          </div>
          <Table>
            <TableHeader>
              <TableRow className="bg-accent/50">
                <TableHead className="text-right font-bold w-12">#</TableHead>
                <TableHead className="text-right font-bold">שם התלמיד</TableHead>
                <TableHead className="text-right font-bold">ציון חזוי</TableHead>
                <TableHead className="text-right font-bold">סיכון נשירה</TableHead>
                <TableHead className="text-right font-bold">רמת סיכון</TableHead>
                <TableHead className="text-right font-bold">גורמים</TableHead>
                <TableHead className="text-right font-bold">פעולות</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {predictionsLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-40" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-8" /></TableCell>
                  </TableRow>
                ))
              ) : predictions?.predictions.length ? (
                predictions.predictions
                  .map((pred, index) => (
                    <TableRow key={pred.student_tz} className="hover:bg-accent/30 transition-colors">
                      <TableCell className="text-muted-foreground">{(page - 1) * pageSize + index + 1}</TableCell>
                      <TableCell className="font-medium">{pred.student_name || "—"}</TableCell>
                      <TableCell
                        className={`font-bold ${(pred.predicted_grade ?? 0) < 55
                            ? "text-red-600"
                            : (pred.predicted_grade ?? 0) >= 80
                              ? "text-green-600"
                              : ""
                          }`}
                      >
                        {pred.predicted_grade?.toFixed(1) ?? "—"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress
                            value={(pred.dropout_risk ?? 0) * 100}
                            className="w-20 h-2"
                          />
                          <span className="text-sm">{((pred.dropout_risk ?? 0) * 100).toFixed(0)}%</span>
                        </div>
                      </TableCell>
                      <TableCell>{getRiskBadge(pred.risk_level ?? "low")}</TableCell>
                      <TableCell className="max-w-[200px]">
                        <div className="text-sm text-muted-foreground truncate">
                          {pred.factors?.slice(0, 2).join(", ") || "—"}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link to="/students/$studentTz" params={{ studentTz: pred.student_tz }}>
                          <Button variant="ghost" size="icon" aria-label="צפה בתלמיד" className="text-primary">
                            <Eye className="size-4" />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                    אין תחזיות זמינות. אמן את המודל תחילה.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {predictions && (
            <div className="p-4 border-t text-sm text-muted-foreground flex items-center gap-2">
              <Clock className="size-4" />
              נוצר ב: {new Date(predictions.generated_at).toLocaleString("he-IL")}
            </div>
          )}
          <TablePagination
            page={page}
            totalPages={Math.ceil(totalPredictions / pageSize)}
            onPageChange={setPage}
          />
        </Card>
      )}

      {/* Not trained message */}
      {!status?.trained && !statusLoading && (
        <Card>
          <CardContent className="p-12 text-center">
            <Brain className="size-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-bold mb-2">המודל לא אומן עדיין</h3>
            <p className="text-muted-foreground mb-6">
              כדי לראות תחזיות על התלמידים, יש לאמן את המודל על הנתונים הקיימים
            </p>
            <Button onClick={() => trainMutation.mutate()} disabled={trainMutation.isPending}>
              <RefreshCw className={`size-4 ml-2 ${trainMutation.isPending ? "animate-spin" : ""}`} />
              {trainMutation.isPending ? "מאמן..." : "אמן מודל עכשיו"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
