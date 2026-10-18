export interface SupportContext {
  appVersion?: unknown;
  buildCommit?: unknown;
  apiContractVersion?: unknown;
  metadataSchemaVersion?: unknown;
  methodId?: unknown;
  catalogMethodIds?: readonly string[];
}

export type ServerConnection = "unknown" | "connected" | "unreachable";

interface SupportObservation {
  errorCode: string | null;
  correlationId: string | null;
  serverConnection: ServerConnection;
}

export interface SupportDiagnostics {
  schema_version: 1;
  created_at: string;
  app_version: string | null;
  build_commit: string | null;
  api_contract_version: number | null;
  metadata_schema_version: number | null;
  locale: "ko" | "en" | "unknown";
  viewport: { width: number | null; height: number | null };
  method_id: string | null;
  error_code: string | null;
  correlation_id: string | null;
  server_connection: ServerConnection;
}

export interface FeedbackDraft {
  problemType: "problem" | "suggestion" | "other";
  reproduction: string;
  expected: string;
  actual: string;
  repeatability: "always" | "sometimes" | "once" | "unknown";
}

export function serializeFeedback(draft: FeedbackDraft, diagnostics: SupportDiagnostics): string {
  return JSON.stringify({
    feedback_schema_version: 1,
    user_feedback: {
      problem_type: draft.problemType,
      reproduction: draft.reproduction,
      expected: draft.expected,
      actual: draft.actual,
      repeatability: draft.repeatability,
    },
    diagnostics,
  }, null, 2);
}

export async function copyFeedbackText(
  text: string,
  clipboard: Pick<Clipboard, "writeText"> | undefined,
): Promise<"copied" | "manual"> {
  try {
    if (clipboard === undefined) return "manual";
    await clipboard.writeText(text);
    return "copied";
  } catch {
    return "manual";
  }
}

// One sanitized observation for this page lifetime, never a request/body/log history.
let observation: SupportObservation = {
  errorCode: null,
  correlationId: null,
  serverConnection: "unknown",
};

export function clearSupportObservation(): void {
  observation = { errorCode: null, correlationId: null, serverConnection: "unknown" };
}

export function readSupportObservation(): SupportObservation {
  return {
    errorCode: observation.errorCode,
    correlationId: observation.correlationId,
    serverConnection: observation.serverConnection,
  };
}

export function observeApiResponse(): void {
  observation.serverConnection = "connected";
}

export function observeNetworkFailure(): void {
  observation = { errorCode: "api_unreachable", correlationId: null, serverConnection: "unreachable" };
}

export function observeApiFailure(error: {
  code: unknown;
  correlationId: unknown;
  status: unknown;
}): void {
  observation = {
    errorCode: validatedString(error.code, /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/u, 80),
    correlationId: validatedString(error.correlationId, /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u, 36),
    serverConnection: typeof error.status === "number" && Number.isInteger(error.status)
      && error.status >= 100 && error.status <= 599 ? "connected" : "unknown",
  };
}

export function buildSupportDiagnostics(
  context: SupportContext,
  options: { locale: unknown; width?: unknown; height?: unknown; now?: Date },
): SupportDiagnostics {
  const method = validatedString(context.methodId, /^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/u, 100);
  const current = readSupportObservation();
  return {
    schema_version: 1,
    created_at: (options.now ?? new Date()).toISOString(),
    app_version: validatedString(context.appVersion, /^\d+\.\d+\.\d+(?:[-+][a-zA-Z0-9.-]+)?$/u, 64),
    build_commit: validatedString(context.buildCommit, /^(?:[0-9a-f]{40}|archive-sha256-[0-9a-f]{64})$/u, 80),
    api_contract_version: positiveInteger(context.apiContractVersion, 10000),
    metadata_schema_version: positiveInteger(context.metadataSchemaVersion, 10000),
    locale: options.locale === "ko" || options.locale === "en" ? options.locale : "unknown",
    viewport: { width: positiveInteger(options.width, 32768), height: positiveInteger(options.height, 32768) },
    method_id: method !== null && context.catalogMethodIds?.includes(method) ? method : null,
    error_code: current.errorCode,
    correlation_id: current.correlationId,
    server_connection: current.serverConnection,
  };
}

function validatedString(value: unknown, pattern: RegExp, maxLength: number): string | null {
  return typeof value === "string" && value.length <= maxLength && pattern.test(value) ? value : null;
}

function positiveInteger(value: unknown, maximum: number): number | null {
  return typeof value === "number" && Number.isInteger(value) && value > 0 && value <= maximum ? value : null;
}
