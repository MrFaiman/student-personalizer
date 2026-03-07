import { create } from "zustand";
import type { FilterState } from "./types/filters";

interface FilterStore extends FilterState {
    setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
    resetFilters: () => void;
}

const defaultFilters: FilterState = {
    year: undefined,
    period: undefined,
    gradeLevel: undefined,
    classId: undefined,
    teacher: undefined,
};

export const useFilterStore = create<FilterStore>((set) => ({
    ...defaultFilters,
    setFilter: (key, value) => set((state) => ({ ...state, [key]: value })),
    resetFilters: () => set(defaultFilters),
}));
