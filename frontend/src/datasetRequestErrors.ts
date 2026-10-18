export function datasetRequestErrorCode(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null && "code" in error &&
      typeof error.code === "string" && /^[a-z][a-z0-9_]{0,127}$/.test(error.code)) {
    return error.code;
  }
  return fallback;
}
