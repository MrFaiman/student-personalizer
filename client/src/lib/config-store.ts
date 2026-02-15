import { create } from "zustand";
import { configApi } from "./api";

interface ConfigState {
  // Server-served constants with sensible defaults
  atRiskGradeThreshold: number;
  mediumGradeThreshold: number;
  goodGradeThreshold: number;
  excellentGradeThreshold: number;
  performanceGoodThreshold: number;
  performanceMediumThreshold: number;
  defaultPageSize: number;
  gradeRange: [number, number];

  // Meta
  isReady: boolean;
  fetch: () => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set) => ({
  // Defaults matching server values so the app works before fetch completes
  atRiskGradeThreshold: 55,
  mediumGradeThreshold: 70,
  goodGradeThreshold: 80,
  excellentGradeThreshold: 85,
  performanceGoodThreshold: 70,
  performanceMediumThreshold: 40,
  defaultPageSize: 20,
  gradeRange: [0, 100],

  isReady: false,

  fetch: async () => {
    try {
      const config = await configApi.get();
      set({
        atRiskGradeThreshold: config.at_risk_grade_threshold,
        mediumGradeThreshold: config.medium_grade_threshold,
        goodGradeThreshold: config.good_grade_threshold,
        excellentGradeThreshold: config.excellent_grade_threshold,
        performanceGoodThreshold: config.performance_good_threshold,
        performanceMediumThreshold: config.performance_medium_threshold,
        defaultPageSize: config.default_page_size,
        gradeRange: config.grade_range,
        isReady: true,
      });
    } catch {
      // Keep defaults if fetch fails; app remains functional
      set({ isReady: true });
    }
  },
}));
