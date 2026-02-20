import { z } from "zod";

export const ImportResponseSchema = z.object({
    batch_id: z.string(),
    file_type: z.enum(["grades", "events", "unknown"]),
    rows_imported: z.number(),
    rows_failed: z.number(),
    students_created: z.number(),
    classes_created: z.number(),
    errors: z.array(z.string()),
});
export type ImportResponse = z.infer<typeof ImportResponseSchema>;

export const ImportLogResponseSchema = z.object({
    id: z.number(),
    batch_id: z.string(),
    filename: z.string(),
    file_type: z.string(),
    rows_imported: z.number(),
    rows_failed: z.number(),
    period: z.string(),
    created_at: z.string(),
});
export type ImportLogResponse = z.infer<typeof ImportLogResponseSchema>;

export const ImportLogListResponseSchema = z.object({
    items: z.array(ImportLogResponseSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
});
export type ImportLogListResponse = z.infer<typeof ImportLogListResponseSchema>;
