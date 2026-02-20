import { z } from "zod";

export const AppConfigSchema = z.object({
    at_risk_grade_threshold: z.number(),
    medium_grade_threshold: z.number(),
    good_grade_threshold: z.number(),
    excellent_grade_threshold: z.number(),
    performance_good_threshold: z.number(),
    performance_medium_threshold: z.number(),
    default_page_size: z.number(),
    grade_range: z.tuple([z.number(), z.number()]),
});
export type AppConfig = z.infer<typeof AppConfigSchema>;
