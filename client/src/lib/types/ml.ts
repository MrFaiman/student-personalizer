import { z } from "zod";

export const TrainResponseSchema = z.object({
    status: z.string(),
    samples: z.number(),
    grade_model_mae: z.number(),
    grade_model_median_ae: z.number().nullable().optional(),
    dropout_model_accuracy: z.number(),
    dropout_model_roc_auc: z.number().nullable().optional(),
    dropout_model_pr_auc: z.number().nullable().optional(),
    dropout_precision_high_risk: z.number().nullable().optional(),
    dropout_recall_high_risk: z.number().nullable().optional(),
    dropout_confusion_matrix: z.array(z.array(z.number())).nullable().optional(),
    grade_feature_importances: z.record(z.string(), z.number()),
    dropout_feature_importances: z.record(z.string(), z.number()),
    class_distribution: z.record(z.string(), z.number()).nullable().optional(),
    cv_folds_grade: z.number().nullable().optional(),
    cv_folds_dropout: z.number().nullable().optional(),
    evaluation_strategy: z.string().nullable().optional(),
    high_risk_threshold: z.number().nullable().optional(),
    medium_risk_threshold: z.number().nullable().optional(),
});
export type TrainResponse = z.infer<typeof TrainResponseSchema>;

export const StudentFeaturesSchema = z.object({
    average_grade: z.number(),
    min_grade: z.number(),
    max_grade: z.number(),
    grade_std: z.number(),
    grade_trend_slope: z.number(),
    num_subjects: z.number(),
    failing_subjects: z.number(),
    absence: z.number(),
    absence_justified: z.number(),
    late: z.number(),
    disturbance: z.number(),
    total_absences: z.number(),
    total_negative_events: z.number(),
    total_positive_events: z.number(),
});

export const StudentPredictionSchema = z.object({
    student_tz: z.string(),
    student_name: z.string(),
    predicted_grade: z.number(),
    dropout_risk: z.number(),
    risk_level: z.enum(["low", "medium", "high"]),
    features: StudentFeaturesSchema,
    factors: z.array(z.string()).optional(),
});
export type StudentPrediction = z.infer<typeof StudentPredictionSchema>;

export const BatchPredictionResponseSchema = z.object({
    predictions: z.array(StudentPredictionSchema),
    model_trained: z.boolean().optional(),
    total_students: z.number().optional(),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    high_risk_count: z.number(),
    medium_risk_count: z.number(),
});
export type BatchPredictionResponse = z.infer<typeof BatchPredictionResponseSchema>;

export const ModelStatusResponseSchema = z.object({
    trained: z.boolean(),
    trained_at: z.string().nullable(),
    samples: z.number().nullable(),
    grade_model_mae: z.number().nullable(),
    grade_model_median_ae: z.number().nullable().optional(),
    dropout_model_accuracy: z.number().nullable(),
    dropout_model_roc_auc: z.number().nullable().optional(),
    dropout_model_pr_auc: z.number().nullable().optional(),
    dropout_precision_high_risk: z.number().nullable().optional(),
    dropout_recall_high_risk: z.number().nullable().optional(),
    evaluation_strategy: z.string().nullable().optional(),
    cv_folds_grade: z.number().nullable().optional(),
    cv_folds_dropout: z.number().nullable().optional(),
});
export type ModelStatusResponse = z.infer<typeof ModelStatusResponseSchema>;
