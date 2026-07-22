export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return "http://127.0.0.1:8000";
}

export async function fetchApi(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("api_unreachable");
    }
    throw error;
  }
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly routeNotFound: boolean;
  readonly correlationId: string | null;

  constructor({
    status,
    code,
    message,
    routeNotFound,
    correlationId,
  }: {
    status: number;
    code: string;
    message: string;
    routeNotFound: boolean;
    correlationId: string | null;
  }) {
    super(code);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.routeNotFound = routeNotFound;
    this.correlationId = correlationId;
    Object.defineProperty(this, "message", { value: message, enumerable: true });
  }
}

export async function apiRequestError(
  response: Response,
  fallback: string,
): Promise<ApiRequestError> {
  let backendCode: string | null = null;
  let backendMessage: string | null = null;
  let correlationId: string | null = null;
  let detail: string | null = null;
  try {
    const payload: unknown = await response.json();
    if (typeof payload === "object" && payload !== null) {
      const record = payload as Record<string, unknown>;
      if (typeof record.detail === "string") detail = record.detail;
      const error = record.error;
      if (typeof error === "object" && error !== null) {
        const errorRecord = error as Record<string, unknown>;
        if (typeof errorRecord.code === "string") backendCode = errorRecord.code;
        if (typeof errorRecord.message === "string") backendMessage = errorRecord.message;
        if (typeof errorRecord.correlation_id === "string") {
          correlationId = errorRecord.correlation_id;
        }
      }
    }
  } catch {
    // A non-JSON error body is represented by the typed fallback below.
  }
  const routeNotFound =
    response.status === 404 &&
    (backendCode === "not_found" || detail?.toLowerCase() === "not found");
  return new ApiRequestError({
    status: response.status,
    code: routeNotFound ? "api_contract_mismatch" : (backendCode ?? fallback),
    message: backendMessage ?? detail ?? fallback,
    routeNotFound,
    correlationId,
  });
}

export async function apiErrorCode(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (typeof payload === "object" && payload !== null) {
      const error = (payload as Record<string, unknown>).error;
      if (typeof error === "object" && error !== null) {
        const code = (error as Record<string, unknown>).code;
        if (typeof code === "string" && code.length > 0) {
          return code;
        }
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export function filenameFromContentDisposition(value: string | null): string | null {
  if (value === null) {
    return null;
  }
  const quoted = /filename="([^"]+)"/i.exec(value);
  if (quoted !== null) {
    return quoted[1];
  }
  const unquoted = /filename=([^;]+)/i.exec(value);
  return unquoted === null ? null : unquoted[1].trim();
}

export function triggerBrowserDownload(blob: Blob, filename: string): void {
  if (typeof document === "undefined") {
    return;
  }

  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
