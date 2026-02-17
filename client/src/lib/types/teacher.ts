export interface TeacherListItem {
    id: string;
    name: string;
    subjects: string[];
    student_count: number;
    average_grade: number | null;
}

export interface TeacherDetailStats {
    student_count: number;
    average_grade: number;
    at_risk_count: number;
    classes_count: number;
}

export interface TeacherClassDetail {
    id: string;
    name: string;
    student_count: number;
    average_grade: number;
    at_risk_count: number;
}

export interface GradeHistogramBin {
    grade: number;
    count: number;
}

export interface TeacherDetailResponse {
    id: string;
    name: string;
    stats: TeacherDetailStats;
    subjects: string[];
    classes: TeacherClassDetail[];
    grade_histogram: GradeHistogramBin[];
}
