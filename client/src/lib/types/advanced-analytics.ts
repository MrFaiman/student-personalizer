// Period Comparison Types
export interface PeriodComparisonItem {
  id: string;
  name: string;
  period_a_average: number | null;
  period_b_average: number | null;
  change: number | null;
  change_percent: number | null;
  student_count_a: number;
  student_count_b: number;
  teacher_name?: string;
  subject?: string;
  class_name?: string;
}

export interface PeriodComparisonResponse {
  comparison_type: "class" | "subject_teacher" | "subject";
  period_a: string;
  period_b: string;
  data: PeriodComparisonItem[];
}

// Red Student Types
export interface RedStudentGroup {
  id: string;
  name: string;
  red_student_count: number;
  total_student_count: number;
  percentage: number;
  average_grade: number;
}

export interface FailingSubject {
  subject: string;
  teacher_name: string | null;
  grade: number;
}

export interface RedStudentDetail {
  student_tz: string;
  student_name: string;
  class_name: string | null;
  grade_level: string | null;
  average_grade: number;
  failing_subjects: FailingSubject[];
}

export interface RedStudentSegmentation {
  total_red_students: number;
  threshold: number;
  by_class: RedStudentGroup[];
  by_layer: RedStudentGroup[];
  by_teacher: RedStudentGroup[];
  by_subject: RedStudentGroup[];
}

export interface RedStudentListResponse {
  total: number;
  page: number;
  page_size: number;
  students: RedStudentDetail[];
}

// Versus Comparison Types
export interface VersusSeriesItem {
  id: string;
  name: string;
  value: number;
  student_count: number;
  subjects?: string[];
  teacher_name?: string;
}

export interface VersusChartData {
  comparison_type: "class" | "teacher" | "layer";
  metric: string;
  series: VersusSeriesItem[];
}

// Cascading Filter Types
export interface ClassOption {
  id: string;
  class_name: string;
  grade_level: string;
}

export interface TeacherOption {
  id: string | null;
  name: string;
  subjects: string[];
}

export interface CascadingFilterOptions {
  classes: ClassOption[];
  teachers: TeacherOption[];
  subjects: string[];
}
