import { fetchApi } from "./core";

import type { AppConfig } from "../types";

export const configApi = {
  get: () => fetchApi<AppConfig>("/api/config"),
};
