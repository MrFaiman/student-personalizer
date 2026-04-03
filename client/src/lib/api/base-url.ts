/** API origin; separate from `core` to avoid a circular import with `auth-store`. */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";
