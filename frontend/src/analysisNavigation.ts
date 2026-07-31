import type { AnalysisMethodListResponse, AnalysisModuleId } from "./api";

export interface AnalysisSelection {
  moduleId: AnalysisModuleId;
  methodId: string;
}

export const CURRENT_RESPONSE_OPTIMIZER_SELECTION: AnalysisSelection = {
  moduleId: "doe",
  methodId: "doe.response_optimizer",
};

const legacyResponseOptimizerSelection: AnalysisSelection = {
  moduleId: "regression",
  methodId: "regression.response_optimizer",
};

const moduleIds = new Set<string>([
  "exploration",
  "hypothesis",
  "categorical",
  "regression",
  "quality",
  "doe",
]);

export function buildAnalysisHash(moduleId: AnalysisModuleId, methodId: string): string {
  return `analysis/${moduleId}/${encodeURIComponent(methodId)}`;
}

export function buildAnalysisPath(moduleId: AnalysisModuleId, methodId: string): string {
  return `/analysis/${moduleId}/${encodeURIComponent(methodId)}`;
}

export function analysisMethodDisplayLabel(
  methodId: string,
  catalog: AnalysisMethodListResponse | null,
  fallback = methodId,
): string {
  const canonicalMethodId =
    methodId === legacyResponseOptimizerSelection.methodId
      ? CURRENT_RESPONSE_OPTIMIZER_SELECTION.methodId
      : methodId;
  return (
    catalog?.methods.find((method) => method.method_id === canonicalMethodId)
      ?.label_ko ?? fallback
  );
}

export function parseAnalysisHash(hash: string): AnalysisSelection | null {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  const parts = normalized.split("/");
  if (parts.length !== 3) {
    return null;
  }
  const [prefix, moduleId, encodedMethodId] = parts;
  if (prefix !== "analysis" || !moduleIds.has(moduleId) || !encodedMethodId) {
    return null;
  }

  try {
    return canonicalAnalysisSelection({
      moduleId: moduleId as AnalysisModuleId,
      methodId: decodeURIComponent(encodedMethodId),
    });
  } catch {
    return null;
  }
}

export function parseAnalysisPath(pathname: string): AnalysisSelection | null {
  const normalized = pathname.startsWith("/") ? pathname.slice(1) : pathname;
  const parts = normalized.split("/");
  if (parts.length !== 3) {
    return null;
  }
  const [prefix, moduleId, encodedMethodId] = parts;
  if (prefix !== "analysis" || !moduleIds.has(moduleId) || !encodedMethodId) {
    return null;
  }

  try {
    return canonicalAnalysisSelection({
      moduleId: moduleId as AnalysisModuleId,
      methodId: decodeURIComponent(encodedMethodId),
    });
  } catch {
    return null;
  }
}

export function parseAnalysisLocation(pathname: string, hash: string): AnalysisSelection | null {
  return parseAnalysisPath(pathname) ?? parseAnalysisHash(hash);
}

export function legacyResponseOptimizerRedirectLocation(
  pathname: string,
  search: string,
  hash: string,
): string | null {
  const pathSelection = parseRawAnalysisPath(pathname);
  const hashSelection = parseRawAnalysisHash(hash);
  if (
    !isLegacyResponseOptimizerSelection(pathSelection) &&
    !isLegacyResponseOptimizerSelection(hashSelection)
  ) {
    return null;
  }
  return `${buildAnalysisPath(
    CURRENT_RESPONSE_OPTIMIZER_SELECTION.moduleId,
    CURRENT_RESPONSE_OPTIMIZER_SELECTION.methodId,
  )}${search}`;
}

function canonicalAnalysisSelection(selection: AnalysisSelection): AnalysisSelection {
  return isLegacyResponseOptimizerSelection(selection)
    ? CURRENT_RESPONSE_OPTIMIZER_SELECTION
    : selection;
}

function isLegacyResponseOptimizerSelection(
  selection: AnalysisSelection | null,
): boolean {
  return (
    selection?.moduleId === legacyResponseOptimizerSelection.moduleId &&
    selection.methodId === legacyResponseOptimizerSelection.methodId
  );
}

function parseRawAnalysisPath(pathname: string): AnalysisSelection | null {
  const normalized = pathname.startsWith("/") ? pathname.slice(1) : pathname;
  return parseRawAnalysisParts(normalized.split("/"));
}

function parseRawAnalysisHash(hash: string): AnalysisSelection | null {
  const normalized = hash.startsWith("#") ? hash.slice(1) : hash;
  return parseRawAnalysisParts(normalized.split("/"));
}

function parseRawAnalysisParts(parts: string[]): AnalysisSelection | null {
  if (parts.length !== 3) return null;
  const [prefix, moduleId, encodedMethodId] = parts;
  if (prefix !== "analysis" || !moduleIds.has(moduleId) || !encodedMethodId) {
    return null;
  }
  try {
    return {
      moduleId: moduleId as AnalysisModuleId,
      methodId: decodeURIComponent(encodedMethodId),
    };
  } catch {
    return null;
  }
}
