import type { ReactNode } from "react";
import { useFilterStore } from "@/lib/filter-store";
import type { FilterState } from "@/lib/types";

export function FilterProvider({ children }: { children: ReactNode }) {
    return <>{children}</>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFilters() {
    const store = useFilterStore();
    const filters: FilterState = {
        year: store.year,
        period: store.period,
        gradeLevel: store.gradeLevel,
        classId: store.classId,
        teacher: store.teacher,
    };
    return {
        filters,
        setFilter: store.setFilter,
        resetFilters: store.resetFilters,
    };
}
