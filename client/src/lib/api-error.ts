export interface ApiErrorData {
  detail?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly data: ApiErrorData;

  constructor(status: number, message: string, data: ApiErrorData = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = ApiError.getStatusText(status);
    this.data = data;
  }

  static isApiError(error: unknown): error is ApiError {
    return error instanceof ApiError;
  }

  static fromResponse(response: Response, data: ApiErrorData = {}): ApiError {
    const message = data.detail || `HTTP error ${response.status}`;
    return new ApiError(response.status, message, data);
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isBadRequest(): boolean {
    return this.status === 400;
  }

  private static getStatusText(status: number): string {
    const statusTexts: Record<number, string> = {
      400: "Bad Request",
      401: "Unauthorized",
      403: "Forbidden",
      404: "Not Found",
      405: "Method Not Allowed",
      408: "Request Timeout",
      409: "Conflict",
      422: "Unprocessable Entity",
      429: "Too Many Requests",
      500: "Internal Server Error",
      502: "Bad Gateway",
      503: "Service Unavailable",
      504: "Gateway Timeout",
    };
    return statusTexts[status] || "Unknown Error";
  }
}
