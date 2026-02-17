import { useQuery } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { advancedAnalyticsApi } from "../lib/api";

export interface CascadingFilterState {
  gradeLevel: string | undefined;
  classId: string | undefined;
  teacherId: string | undefined;
  subject: string | undefined;
  periodA: string | undefined;
  periodB: string | undefined;
}

export function useCascadingFilters(initialPeriods: string[] = []) {
  const [filters, setFilters] = useState<CascadingFilterState>({
    gradeLevel: undefined,
    classId: undefined,
    teacherId: undefined,
    subject: undefined,
    periodA: initialPeriods[0],
    periodB: initialPeriods[1],
  });

  // Fetch available options based on current selections
  const { data: options, isLoading } = useQuery({
    queryKey: [
      "cascading-filters",
      filters.gradeLevel,
      filters.classId,
      filters.periodA,
    ],
    queryFn: () =>
      advancedAnalyticsApi.getCascadingFilterOptions({
        grade_level: filters.gradeLevel,
        class_id: filters.classId,
        period: filters.periodA,
      }),
    staleTime: 30000,
  });

  // Reset child filters when parent changes
  const setGradeLevel = useCallback((value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      gradeLevel: value,
      classId: undefined, // Reset child
      teacherId: undefined,
      subject: undefined,
    }));
  }, []);

  const setClassId = useCallback((value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      classId: value,
      teacherId: undefined, // Reset children
      subject: undefined,
    }));
  }, []);

  const setTeacherId = useCallback((value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      teacherId: value,
      subject: undefined, // Reset child
    }));
  }, []);

  const setSubject = useCallback((value: string | undefined) => {
    setFilters((prev) => ({ ...prev, subject: value }));
  }, []);

  const setPeriodA = useCallback((value: string | undefined) => {
    setFilters((prev) => ({ ...prev, periodA: value }));
  }, []);

  const setPeriodB = useCallback((value: string | undefined) => {
    setFilters((prev) => ({ ...prev, periodB: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      gradeLevel: undefined,
      classId: undefined,
      teacherId: undefined,
      subject: undefined,
      periodA: initialPeriods[0],
      periodB: initialPeriods[1],
    });
  }, [initialPeriods]);

  return {
    filters,
    options,
    isLoading,
    setGradeLevel,
    setClassId,
    setTeacherId,
    setSubject,
    setPeriodA,
    setPeriodB,
    resetFilters,
  };
}
