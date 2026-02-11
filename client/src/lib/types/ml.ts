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
    trained_at: string | null;
    samples: number | null;
    grade_model_mae: number | null;
    dropout_model_accuracy: number | null;
}
