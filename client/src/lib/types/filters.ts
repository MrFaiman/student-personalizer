import { z } from "zod";

export const FilterStateSchema = z.object({
    year: z.string().optional(),
    period: z.string().optional(),
    gradeLevel: z.string().optional(),
    classId: z.string().optional(),
    teacher: z.string().optional(),
});
export type FilterState = z.infer<typeof FilterStateSchema>;
