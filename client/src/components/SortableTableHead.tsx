import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import { TableHead } from "@/components/ui/table";
import type { SortState } from "@/hooks/useTableSort";

interface SortableTableHeadProps<T extends string = string> {
    column: T;
    sort: SortState<T>;
    onSort: (column: T) => void;
    children: React.ReactNode;
    className?: string;
}

export function SortableTableHead<T extends string = string>({
    column,
    sort,
    onSort,
    children,
    className = "",
}: SortableTableHeadProps<T>) {
    const isActive = sort.column === column;

    return (
        <TableHead
            className={`text-right font-bold cursor-pointer select-none hover:bg-accent/80 transition-colors ${className}`}
            onClick={() => onSort(column)}
            role="columnheader"
            aria-sort={isActive ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
        >
            <span className="inline-flex items-center gap-1">
                {children}
                {isActive ? (
                    sort.direction === "asc" ? (
                        <ArrowUp className="size-3.5 text-primary" />
                    ) : (
                        <ArrowDown className="size-3.5 text-primary" />
                    )
                ) : (
                    <ArrowUpDown className="size-3.5 text-muted-foreground/50" />
                )}
            </span>
        </TableHead>
    );
}
