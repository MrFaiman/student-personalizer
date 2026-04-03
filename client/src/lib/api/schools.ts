import { SchoolOptionsSchema, type SchoolOption } from "../types/auth";
import { buildQueryString, fetchApi } from "./core";

export function searchSchools(q: string, limit = 50): Promise<SchoolOption[]> {
  return fetchApi(
    `/api/auth/schools/search${buildQueryString({ q, limit })}`,
    undefined,
    SchoolOptionsSchema,
  );
}
