export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl.replace(/\/+$/u, "");
  }
  return "";
}

import { getCurrentLocale } from "../i18n/store";

export async function fetchApi(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const headers = localeHeaders(init?.headers ?? (input instanceof Request ? input.headers : undefined));
  try {
    return await fetch(input, { ...init, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("api_unreachable");
    }
    throw error;
  }
}

function localeHeaders(existing: HeadersInit | undefined): HeadersInit {
  const headers = new Headers(existing);
  headers.set("Accept-Language", getCurrentLocale());
  return headers;
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
  if (value === null) return null;
  let fallback: string | null = null;
  let extended: string | null = null;
  const parameters = /(?:^|;)\s*(filename\*?)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^;]*))/giu;
  for (const match of value.matchAll(parameters)) {
    const name = (match[2] ?? match[3]).trim();
    if (match[1].toLowerCase() === "filename*") {
      const utf8 = /^utf-8'[^']*'(.*)$/iu.exec(name);
      if (utf8 === null) continue;
      try { extended ??= safeDownloadFilename(decodeURIComponent(utf8[1])); }
      catch { /* A malformed extended parameter may use the plain fallback. */ }
    } else {
      fallback ??= safeDownloadFilename(name.replace(/\\(["\\])/gu, "$1"));
    }
  }
  return extended ?? fallback;
}

function safeDownloadFilename(value: string): string | null {
  const basename = value.split(/[\\/]/u).at(-1) ?? "";
  // A server filename is advisory: retain Unicode text, never filesystem paths.
  const clean = Array.from(basename)
    .filter((character) => {
      const code = character.codePointAt(0)!;
      return code > 31 && !(code >= 127 && code <= 159)
        && !(code >= 0x202a && code <= 0x202e) && !(code >= 0x2066 && code <= 0x2069);
    }).join("").replace(/[<>:"|?*]/gu, "_").replace(/^[. ]+|[. ]+$/gu, "");
  if (clean.length === 0) return null;
  return /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/iu.test(clean) ? `_${clean}` : clean;
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
