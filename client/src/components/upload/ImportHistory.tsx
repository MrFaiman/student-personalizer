import { useTranslation } from "react-i18next";
import { Clock, Trash2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TablePagination } from "@/components/TablePagination";
import { SortableTableHead } from "@/components/SortableTableHead";
import { formatHebrewYear } from "@/lib/hebrew-year";
import type { SortState } from "@/hooks/useTableSort";

interface ImportLog {
  batch_id: string;
  filename: string;
  file_type: string;
  year: string | null;
  period: string;
  rows_imported: number;
  rows_failed: number;
  created_at: string;
}

interface ImportHistoryProps {
  logs: { items: ImportLog[]; total: number } | undefined;
  isLoading: boolean;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  sort: SortState<string>;
  onSort: (column: string) => void;
  onDelete: (batchId: string) => void;
  isDeleting: boolean;
}

export function ImportHistory({
  logs,
  isLoading,
  page,
  pageSize,
  onPageChange,
  sort,
  onSort,
  onDelete,
  isDeleting,
}: ImportHistoryProps) {
  const { t } = useTranslation("upload");

  return (
    <Card>
      <div className="p-4 border-b">
        <h3 className="text-base font-bold flex items-center gap-2">
          <Clock className="size-4 text-muted-foreground" />
          {t("history.title")}
        </h3>
      </div>
      <Table>
        <TableHeader>
          <TableRow className="bg-accent/50">
            <TableHead className="text-right font-bold w-12 text-xs">
              #
            </TableHead>
            <SortableTableHead
              column="filename"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.file")}
            </SortableTableHead>
            <SortableTableHead
              column="file_type"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.type")}
            </SortableTableHead>
            <SortableTableHead
              column="year"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.year")}
            </SortableTableHead>
            <SortableTableHead
              column="period"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.period")}
            </SortableTableHead>
            <SortableTableHead
              column="rows_imported"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.rows")}
            </SortableTableHead>
            <SortableTableHead
              column="created_at"
              sort={sort}
              onSort={onSort}
              className="text-xs"
            >
              {t("history.date")}
            </SortableTableHead>
            <TableHead className="text-right font-bold text-xs">
              {t("history.status")}
            </TableHead>
            <TableHead className="text-right font-bold w-12 text-xs">
              {t("history.actions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {Array.from({ length: 9 }).map((__, j) => (
                  <TableCell key={j} className="py-2">
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : logs?.items?.length ? (
            logs.items.map((log, index) => (
              <TableRow key={log.batch_id}>
                <TableCell className="text-muted-foreground text-xs py-2">
                  {(page - 1) * pageSize + index + 1}
                </TableCell>
                <TableCell className="font-medium text-sm py-2">
                  {log.filename}
                </TableCell>
                <TableCell className="py-2">
                  <Badge variant="outline" className="text-xs">
                    {log.file_type === "grades"
                      ? t("fileType.grades")
                      : t("fileType.events")}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm py-2" dir="ltr">
                  {formatHebrewYear(log.year)}
                </TableCell>
                <TableCell className="text-sm py-2">{log.period}</TableCell>
                <TableCell className="text-sm py-2">
                  {log.rows_imported}
                  {log.rows_failed > 0 && (
                    <span className="text-red-600 mr-1 text-xs">
                      {t("history.failedRows", { count: log.rows_failed })}
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs py-2">
                  {new Date(log.created_at).toLocaleDateString("he-IL")}
                </TableCell>
                <TableCell className="py-2">
                  {log.rows_failed === 0 ? (
                    <Badge className="bg-green-100 text-green-700 text-xs">
                      {t("history.success")}
                    </Badge>
                  ) : (
                    <Badge className="bg-yellow-100 text-yellow-700 text-xs">
                      {t("history.partial")}
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="py-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => onDelete(log.batch_id)}
                    disabled={isDeleting}
                  >
                    <Trash2 className="size-4 text-red-600" />
                  </Button>
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell
                colSpan={9}
                className="text-center text-muted-foreground py-8 text-sm"
              >
                {t("history.noHistory")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <TablePagination
        page={page}
        totalPages={Math.ceil((logs?.total || 0) / pageSize)}
        onPageChange={onPageChange}
      />
    </Card>
  );
}
