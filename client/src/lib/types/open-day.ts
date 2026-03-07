import { z } from "zod";

export const OpenDayRegistrationSchema = z.object({
    id: z.number(),
    import_id: z.number().nullable(),
    submitted_at: z.string().nullable(),
    first_name: z.string(),
    last_name: z.string(),
    student_id: z.string().nullable(),
    parent_name: z.string().nullable(),
    phone: z.string().nullable(),
    email: z.string().nullable(),
    current_school: z.string().nullable(),
    next_grade: z.string().nullable(),
    interested_track: z.string().nullable(),
    referral_source: z.string().nullable(),
    additional_notes: z.string().nullable(),
    import_date: z.string(),
});

export type OpenDayRegistration = z.infer<typeof OpenDayRegistrationSchema>;

export const OpenDayRegistrationListResponseSchema = z.object({
    items: z.array(OpenDayRegistrationSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
});

export type OpenDayRegistrationListResponse = z.infer<typeof OpenDayRegistrationListResponseSchema>;

export const OpenDayImportItemSchema = z.object({
    id: z.number(),
    batch_id: z.string(),
    filename: z.string(),
    rows_imported: z.number(),
    rows_failed: z.number(),
    import_date: z.string(),
});

export type OpenDayImportItem = z.infer<typeof OpenDayImportItemSchema>;

export const OpenDayImportListResponseSchema = z.object({
    items: z.array(OpenDayImportItemSchema),
    total: z.number(),
});

export type OpenDayImportListResponse = z.infer<typeof OpenDayImportListResponseSchema>;

export const OpenDayUploadResponseSchema = z.object({
    batch_id: z.string(),
    rows_imported: z.number(),
    rows_failed: z.number(),
    errors: z.array(z.string()),
});

export type OpenDayUploadResponse = z.infer<typeof OpenDayUploadResponseSchema>;

export const OpenDayStatsSchema = z.object({
    total: z.number(),
    by_track: z.record(z.string(), z.number()),
    by_grade: z.record(z.string(), z.number()),
    by_referral: z.record(z.string(), z.number()),
    by_school: z.record(z.string(), z.number()),
    by_date: z.record(z.string(), z.number()),
    track_by_grade: z.record(z.string(), z.record(z.string(), z.number())),
});

export type OpenDayStats = z.infer<typeof OpenDayStatsSchema>;
