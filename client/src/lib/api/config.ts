import { fetchApi } from "./core";

import { AppConfigSchema } from "../types";

export const configApi = {
  get: () => fetchApi("/api/config", undefined, AppConfigSchema),
};
