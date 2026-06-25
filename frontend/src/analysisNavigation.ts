import type { AnalysisModuleId } from "./api";

export interface AnalysisSelection {
  moduleId: AnalysisModuleId;
  methodId: string;
}

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
    return {
      moduleId: moduleId as AnalysisModuleId,
      methodId: decodeURIComponent(encodedMethodId),
    };
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
    return {
      moduleId: moduleId as AnalysisModuleId,
      methodId: decodeURIComponent(encodedMethodId),
    };
  } catch {
    return null;
  }
}

export function parseAnalysisLocation(pathname: string, hash: string): AnalysisSelection | null {
  return parseAnalysisPath(pathname) ?? parseAnalysisHash(hash);
}
