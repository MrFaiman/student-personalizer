export interface StudentListItem {
    student_tz: string;
    student_name: string;
    class_id: string;
    class_name: string;
    grade_level: string;
    average_grade: number | null;
    total_absences: number;
    is_at_risk: boolean;
}

export interface StudentListResponse {
    items: StudentListItem[];
    total: number;
    page: number;
    page_size: number;
}

export interface StudentDetailResponse {
    student_tz: string;
    student_name: string;
    class_id: string;
    class_name: string;
    grade_level: string;
    average_grade: number | null;
    total_absences: number;
    total_negative_events: number;
    total_positive_events: number;
    is_at_risk: boolean;
    performance_score: number | null;
}

export interface GradeResponse {
    id: number;
    subject: string;
    teacher_name: string | null;
    grade: number;
    period: string;
}

export interface AttendanceResponse {
    id: number;
    lessons_reported: number;
    absence: number;
    absence_justified: number;
    late: number;
    disturbance: number;
    total_absences: number;
    attendance: number;
    total_negative_events: number;
    total_positive_events: number;
    period: string;
}

export interface ClassResponse {
    id: string;
    class_name: string;
    grade_level: string;
    student_count: number;
    average_grade: number | null;
    at_risk_count: number;
}

export interface DashboardStats {
    total_students: number;
    average_grade: number | null;
    at_risk_count: number;
    total_classes: number;
    classes: ClassResponse[];
}
