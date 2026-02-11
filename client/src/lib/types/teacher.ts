export interface TeacherListItem {
    id: string;
    name: string;
    subject_count: number;
    student_count: number;
    average_grade: number | null;
}

export interface GradeHistogramBin {
    grade: number;
    count: number;
}

export interface TeacherClassPerformance {
    class_name: string;
    class_id: string;
    average_grade: number;
    student_count: number;
    distribution: {
        category: string;
        count: number;
    }[];
    grade_histogram: GradeHistogramBin[];
}

export interface TeacherSubjectPerformance {
    subject: string;
    average_grade: number;
    student_count: number;
}

export interface TeacherDetailResponse {
    id: string;
    name: string;
    subjects: string[];
    classes: string[];
    student_count: number;
    average_grade: number | null;
    distribution: {
        category: string;
        count: number;
    }[];
    grade_histogram: GradeHistogramBin[];
    class_performance: TeacherClassPerformance[];
    subject_performance: TeacherSubjectPerformance[];
}
