export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return "http://127.0.0.1:8000";
}

import { getCurrentLocale } from "../i18n/store";
import { resolveLocalizedText, t, translateKnownSource } from "../i18n/translate";

export async function fetchApi(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = localeHeaders(init?.headers);
  const body = typeof init?.body === "string" ? resolveLocalizedText(init.body) : init?.body;
  try {
    const response = await fetch(input, { ...init, body, headers });
    return localizedJsonResponse(response);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("api_unreachable");
    }
    throw error;
  }
}

function localizedJsonResponse(response: Response): Response {
  const readJson = response.json.bind(response);
  Object.defineProperty(response, "json", {
    configurable: true,
    value: async () => localizeApiPayload(await readJson(), getCurrentLocale()),
  });
  return response;
}

export function localizeApiPayload(
  value: unknown,
  locale = getCurrentLocale(),
  contextKey: string | null = null,
): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => localizeApiPayload(item, locale, contextKey));
  }
  if (typeof value !== "object" || value === null) return value;
  const record = value as Record<string, unknown>;
  const localized = Object.fromEntries(
    Object.entries(record).map(([key, item]) => [key, localizeApiPayload(item, locale, key)]),
  );
  const messageContainer =
    contextKey === "error" ||
    contextKey === "errors" ||
    contextKey === "issue" ||
    contextKey === "issues" ||
    contextKey === "warning" ||
    contextKey === "warnings" ||
    typeof record.severity === "string" ||
    typeof record.correlation_id === "string";
  if (
    messageContainer &&
    typeof record.code === "string" &&
    typeof record.message === "string"
  ) {
    localized.message = locale === "ko"
      ? record.message
      : translateKnownSource(record.message, locale) ?? t("warnings.generic", {}, locale);
  }
  return localized;
}

function localeHeaders(existing: HeadersInit | undefined): HeadersInit {
  if (existing instanceof Headers) {
    const headers = new Headers(existing);
    headers.set("Accept-Language", getCurrentLocale());
    return headers;
  }
  if (Array.isArray(existing)) {
    return [
      ...existing.filter(([name]) => name.toLowerCase() !== "accept-language"),
      ["Accept-Language", getCurrentLocale()],
    ];
  }
  return { ...existing, "Accept-Language": getCurrentLocale() };
}

export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly routeNotFound: boolean;
  readonly correlationId: string | null;
  readonly backendMessage: string | null;

  constructor({
    status,
    code,
    backendMessage,
    message,
    routeNotFound,
    correlationId,
  }: {
    status: number;
    code: string;
    backendMessage?: string | null;
    message?: string;
    routeNotFound: boolean;
    correlationId: string | null;
  }) {
    super(code);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.routeNotFound = routeNotFound;
    this.correlationId = correlationId;
    this.backendMessage = backendMessage ?? message ?? null;
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
    backendMessage: backendMessage ?? detail,
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
