export interface AppConfig {
  at_risk_grade_threshold: number;
  medium_grade_threshold: number;
  good_grade_threshold: number;
  excellent_grade_threshold: number;
  performance_good_threshold: number;
  performance_medium_threshold: number;
  default_page_size: number;
  grade_range: [number, number];
}
