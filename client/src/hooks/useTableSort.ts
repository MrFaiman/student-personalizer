import { useState, useMemo, useCallback } from "react";

export type SortDirection = "asc" | "desc";

export interface SortState<T extends string = string> {
    column: T | null;
    direction: SortDirection;
}

export function useTableSort<T extends string = string>(defaultColumn?: T, defaultDirection: SortDirection = "asc") {
    const [sort, setSort] = useState<SortState<T>>({
        column: defaultColumn ?? null,
        direction: defaultDirection,
    });

    const toggleSort = useCallback((column: T) => {
        setSort((prev) => {
            if (prev.column === column) {
                return { column, direction: prev.direction === "asc" ? "desc" : "asc" };
            }
            return { column, direction: "asc" };
        });
    }, []);

    return { sort, toggleSort };
}

/**
 * Client-side sort helper. Sorts an array based on the current sort state.
 * Accessor returns the comparable value for each item.
 */
export function useClientSort<TItem, TCol extends string = string>(
    items: TItem[],
    sort: SortState<TCol>,
    accessors: Partial<Record<TCol, (item: TItem) => string | number | null | undefined>>,
): TItem[] {
    return useMemo(() => {
        if (!sort.column || !items.length) return items;

        const accessor = accessors[sort.column];
        if (!accessor) return items;

        const sorted = [...items].sort((a, b) => {
            const va = accessor(a);
            const vb = accessor(b);

            if (va == null && vb == null) return 0;
            if (va == null) return 1;
            if (vb == null) return -1;

            if (typeof va === "number" && typeof vb === "number") {
                return va - vb;
            }
            return String(va).localeCompare(String(vb), "he");
        });

        if (sort.direction === "desc") sorted.reverse();
        return sorted;
    }, [items, sort.column, sort.direction, accessors]);
}
