import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { FilterState } from "@/lib/types";

interface FilterContextValue {
    filters: FilterState;
    setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
    resetFilters: () => void;
}

const defaultFilters: FilterState = {
    period: undefined,
    gradeLevel: undefined,
    classId: undefined,
    teacher: undefined,
};

const FilterContext = createContext<FilterContextValue | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
    const [filters, setFilters] = useState<FilterState>(defaultFilters);

    const setFilter = useCallback(<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    }, []);

    const resetFilters = useCallback(() => {
        setFilters(defaultFilters);
    }, []);

    return (
        <FilterContext.Provider value={{ filters, setFilter, resetFilters }}>
            {children}
        </FilterContext.Provider>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFilters() {
    const ctx = useContext(FilterContext);
    if (!ctx) {
        throw new Error("useFilters must be used within FilterProvider");
    }
    return ctx;
}
