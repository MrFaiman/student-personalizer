export interface LayerKPIsResponse {
    layer_average: number;
    avg_absences: number;
    at_risk_students: number;
    total_students: number;
}

export interface ClassComparisonItem {
    id: string;
    class_name: string;
    average_grade: number;
    student_count: number;
}

export interface HeatmapStudent {
    student_name: string;
    student_tz: string;
    grades: Record<string, number | null>;
    average: number;
}

export interface HeatmapData {
    subjects: string[];
    students: HeatmapStudent[];
}

export interface StudentRanking {
    student_name: string;
    student_tz: string;
    average: number;
}

export interface TopBottomResponse {
    top: StudentRanking[];
    bottom: StudentRanking[];
}

export interface TeacherStatsResponse {
    teacher_name: string;
    total_students: number;
    average_grade: number;
    distribution: {
        fail: number;
        medium: number;
        good: number;
        excellent: number;
    };
}

export interface SubjectGradeItem {
    subject: string;
    grade: number;
}

export interface MetadataResponse {
    periods: string[];
    grade_levels: string[];
    teachers: string[];
}
