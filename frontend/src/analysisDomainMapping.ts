import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import {
  ANALYSIS_DOMAINS,
  type AnalysisDomainDefinition,
  type AnalysisDomainFamily,
  type AnalysisDomainId,
} from "./analysisDomains";

export interface AnalysisMethodPlacement {
  contextual: boolean;
  domain: AnalysisDomainDefinition;
  family: AnalysisDomainFamily;
}
const placements = new Map<string, AnalysisMethodPlacement>();

for (const domain of ANALYSIS_DOMAINS) {
  for (const family of domain.families) {
    for (const methodId of family.methodIds) {
      addPlacement(methodId, domain, family, false);
    }
    for (const methodId of family.contextualMethodIds ?? []) {
      addPlacement(methodId, domain, family, true);
    }
  }
}

function addPlacement(
  methodId: string,
  domain: AnalysisDomainDefinition,
  family: AnalysisDomainFamily,
  contextual: boolean,
) {
  if (placements.has(methodId)) {
    throw new Error(`duplicate_analysis_domain_method:${methodId}`);
  }
  placements.set(methodId, { contextual, domain, family });
}

export function analysisMethodPlacement(methodId: string): AnalysisMethodPlacement | null {
  return placements.get(methodId) ?? null;
}

export function analysisDomainForMethod(methodId: string): AnalysisDomainDefinition | null {
  return analysisMethodPlacement(methodId)?.domain ?? null;
}

export function analysisFamilyForMethod(methodId: string): AnalysisDomainFamily | null {
  return analysisMethodPlacement(methodId)?.family ?? null;
}

export function analysisDomainById(domainId: string | null): AnalysisDomainDefinition | null {
  return ANALYSIS_DOMAINS.find((domain) => domain.id === domainId) ?? null;
}

export function isAnalysisDomainId(value: string | null): value is AnalysisDomainId {
  return analysisDomainById(value) !== null;
}

export function domainCatalogMethods(
  catalog: AnalysisMethodListResponse,
  domain: AnalysisDomainDefinition,
): AnalysisMethodDescriptor[] {
  const ids = new Set(
    domain.families.flatMap((family) => [...family.methodIds]),
  );
  return catalog.methods.filter((method) => ids.has(method.method_id));
}

export function familyCatalogMethods(
  catalog: AnalysisMethodListResponse,
  family: AnalysisDomainFamily,
): AnalysisMethodDescriptor[] {
  const ids = new Set(family.methodIds);
  return catalog.methods
    .filter((method) => ids.has(method.method_id))
    .sort((left, right) => left.order - right.order);
}

export function contextualCatalogMethods(
  catalog: AnalysisMethodListResponse,
  family: AnalysisDomainFamily,
): AnalysisMethodDescriptor[] {
  const ids = new Set(family.contextualMethodIds ?? []);
  return catalog.methods
    .filter((method) => ids.has(method.method_id))
    .sort((left, right) => left.order - right.order);
}

export function validateAnalysisDomainCatalog(catalog: AnalysisMethodListResponse): string[] {
  const catalogIds = new Set(catalog.methods.map((method) => method.method_id));
  const errors: string[] = [];
  for (const method of catalog.methods) {
    if (!placements.has(method.method_id)) {
      errors.push(`unmapped:${method.method_id}`);
    }
  }
  for (const methodId of placements.keys()) {
    if (!catalogIds.has(methodId)) errors.push(`unknown:${methodId}`);
  }
  return errors;
}

export function mappedAnalysisMethodIds(): string[] {
  return [...placements.keys()];
}
