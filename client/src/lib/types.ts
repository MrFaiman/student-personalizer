/**
 * TypeScript types matching backend Pydantic schemas.
 */

// ========================
// Analytics Types
// ========================

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

// ========================
// Student Types
// ========================

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
    total_lates: number;
    class_average_absences: number;
    is_at_risk: boolean;
    trend: "improving" | "declining" | "stable";
}

export interface GradeResponse {
    subject: string;
    teacher: string;
    grade: number;
    period: string;
    date: string | null;
}

export interface AttendanceResponse {
    event_type: string;
    hours: number;
    date: string;
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
}

// ========================
// Ingestion Types
// ========================

export interface ImportResponse {
    batch_id: string;
    file_type: "grades" | "events" | "unknown";
    rows_imported: number;
    rows_failed: number;
    students_created: number;
    classes_created: number;
    errors: string[];
}

export interface ImportLogResponse {
    id: number;
    batch_id: string;
    filename: string;
    file_type: string;
    rows_imported: number;
    rows_failed: number;
    period: string;
    created_at: string;
}

export interface ImportLogListResponse {
    items: ImportLogResponse[];
    total: number;
    page: number;
    page_size: number;
}

// ========================
// ML Types
// ========================

export interface TrainResponse {
    success: boolean;
    samples_used: number;
    message: string;
}

export interface StudentPrediction {
    student_tz: string;
    student_name: string;
    predicted_grade: number;
    dropout_risk: number;
    risk_level: "low" | "medium" | "high";
    factors: string[];
}

export interface BatchPredictionResponse {
    predictions: StudentPrediction[];
    model_version: string;
    generated_at: string;
    total: number;
    page: number;
    page_size: number;
    high_risk_count: number;
    medium_risk_count: number;
}

export interface ModelStatusResponse {
    trained: boolean;
    last_trained_at: string | null;
    samples_trained: number | null;
    model_version: string | null;
}

// ========================
// Filter Types
// ========================

export interface FilterState {
    period: string | undefined;
    gradeLevel: string | undefined;
    classId: string | undefined;
    teacher: string | undefined;
}
