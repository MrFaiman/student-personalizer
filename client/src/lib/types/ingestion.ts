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
