import { z } from "zod";

export const TrainResponseSchema = z.object({
    status: z.string(),
    samples: z.number(),
    grade_model_mae: z.number(),
    dropout_model_accuracy: z.number(),
    grade_feature_importances: z.record(z.string(), z.number()),
    dropout_feature_importances: z.record(z.string(), z.number()),
});
export type TrainResponse = z.infer<typeof TrainResponseSchema>;

export const StudentPredictionSchema = z.object({
    student_tz: z.string(),
    student_name: z.string(),
    predicted_grade: z.number(),
    dropout_risk: z.number(),
    risk_level: z.enum(["low", "medium", "high"]),
    factors: z.array(z.string()).optional(),
});
export type StudentPrediction = z.infer<typeof StudentPredictionSchema>;

export const BatchPredictionResponseSchema = z.object({
    predictions: z.array(StudentPredictionSchema),
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
    dropout_model_accuracy: z.number().nullable(),
});
export type ModelStatusResponse = z.infer<typeof ModelStatusResponseSchema>;
