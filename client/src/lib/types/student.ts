import { z } from "zod";

export const StudentListItemSchema = z.object({
    student_tz: z.string(),
    student_name: z.string(),
    class_id: z.string(),
    class_name: z.string(),
    grade_level: z.string(),
    average_grade: z.number().nullable(),
    total_absences: z.number(),
    is_at_risk: z.boolean(),
});
export type StudentListItem = z.infer<typeof StudentListItemSchema>;

export const StudentListResponseSchema = z.object({
    items: z.array(StudentListItemSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
});
export type StudentListResponse = z.infer<typeof StudentListResponseSchema>;

export const StudentDetailResponseSchema = z.object({
    student_tz: z.string(),
    student_name: z.string(),
    class_id: z.string(),
    class_name: z.string(),
    grade_level: z.string(),
    average_grade: z.number().nullable(),
    total_absences: z.number(),
    total_negative_events: z.number(),
    total_positive_events: z.number(),
    is_at_risk: z.boolean(),
    performance_score: z.number().nullable(),
});
export type StudentDetailResponse = z.infer<typeof StudentDetailResponseSchema>;

export const GradeResponseSchema = z.object({
    id: z.number(),
    subject: z.string(),
    teacher_name: z.string().nullable(),
    grade: z.number(),
    period: z.string(),
});
export type GradeResponse = z.infer<typeof GradeResponseSchema>;

export const AttendanceResponseSchema = z.object({
    id: z.number(),
    lessons_reported: z.number(),
    absence: z.number(),
    absence_justified: z.number(),
    late: z.number(),
    disturbance: z.number(),
    total_absences: z.number(),
    attendance: z.number(),
    total_negative_events: z.number(),
    total_positive_events: z.number(),
    period: z.string(),
});
export type AttendanceResponse = z.infer<typeof AttendanceResponseSchema>;

export const ClassResponseSchema = z.object({
    id: z.string(),
    class_name: z.string(),
    grade_level: z.string(),
    student_count: z.number(),
    average_grade: z.number().nullable(),
    at_risk_count: z.number(),
});
export type ClassResponse = z.infer<typeof ClassResponseSchema>;

export const DashboardStatsSchema = z.object({
    total_students: z.number(),
    average_grade: z.number().nullable(),
    at_risk_count: z.number(),
    total_classes: z.number(),
    classes: z.array(ClassResponseSchema),
});
export type DashboardStats = z.infer<typeof DashboardStatsSchema>;
