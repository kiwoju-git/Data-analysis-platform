import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import { ANALYSIS_DOMAINS, type AnalysisDomainDefinition } from "./analysisDomains";
import {
  directCatalogMethods,
  domainCatalogMethods,
  validateAnalysisDomainCatalog,
} from "./analysisDomainMapping";
import { domainGuidanceKey } from "./analysisDomainGuidance";
import { AnalysisDomainFamilyCard } from "./AnalysisDomainFamilyCard";
import {
  AnalysisDomainMethodCard,
  ContextualDomainMethodCard,
  PlannedDomainMethodCard,
} from "./AnalysisDomainMethodCard";
import { useI18n } from "./i18n/LocaleProvider";

interface AnalysisDomainLandingProps {
  catalog: AnalysisMethodListResponse;
  domain: AnalysisDomainDefinition | null;
  selectedMethodId: string | null;
  onOpenDomain: (domain: AnalysisDomainDefinition) => void;
  onSelectMethod: (method: AnalysisMethodDescriptor) => void;
}

export function AnalysisDomainLanding({
  catalog,
  domain,
  selectedMethodId,
  onOpenDomain,
  onSelectMethod,
}: AnalysisDomainLandingProps) {
  const { t } = useI18n();
  const mappingErrors = validateAnalysisDomainCatalog(catalog);
  const mappingNotice = mappingErrors.length > 0 ? (
    <div className="error-box" role="alert">
      {t("analysisDomains.mappingError")} <code>{mappingErrors.join(", ")}</code>
    </div>
  ) : null;
  if (domain === null) {
    return (
      <section aria-label={t("analysisDomains.title")}>
        {mappingNotice}
        <div className="analysis-domain-grid">
          {ANALYSIS_DOMAINS.map((candidate) => {
            const methods = domainCatalogMethods(catalog, candidate);
            const planned = candidate.families.reduce(
              (count, family) => count + (family.plannedWorkflows?.length ?? 0),
              candidate.directPlannedWorkflows?.length ?? 0,
            );
            return (
              <button
                className="analysis-domain-card"
                key={candidate.id}
                onClick={() => onOpenDomain(candidate)}
                type="button"
              >
                <span className="analysis-domain-order">{candidate.order}</span>
                <strong>{t(candidate.labelKey)}</strong>
                <span className="analysis-domain-card-description">
                  {t(candidate.descriptionKey)}
                </span>
                <span className="analysis-domain-card-families">
                  {candidate.families.slice(0, 4).map((family) => t(family.labelKey)).join(" · ")}
                </span>
                <span className="analysis-domain-card-meta">
                  {t("analysisDomains.availableCount", {
                    count: methods.filter((method) => method.availability === "available").length,
                  })}
                  {planned > 0
                    ? ` · ${t("analysisDomains.plannedCount", { count: planned })}`
                    : ""}
                </span>
                <span className="analysis-domain-card-action">
                  {t("analysisDomains.open")}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section aria-label={t(domain.labelKey)}>
      <div className="analysis-domain-intro">
        <div className="notice-box analysis-domain-guidance">
          {t(domainGuidanceKey(domain.id))}
        </div>
        {(domain.selectionGuideKeys?.length ?? 0) > 0 ? (
          <ul className="analysis-domain-selection-guide">
            {domain.selectionGuideKeys?.map((key) => <li key={key}>{t(key)}</li>)}
          </ul>
        ) : null}
      </div>
      {mappingNotice}
      {domain.landingMode === "flat_methods" ? (
        <>
          <div className="analysis-domain-method-grid">
            {directCatalogMethods(catalog, domain).map((method) => (
              <AnalysisDomainMethodCard
                key={method.method_id}
                method={method}
                selected={selectedMethodId === method.method_id}
                onSelectMethod={onSelectMethod}
              />
            ))}
            {(domain.directPlannedWorkflows ?? []).map((workflow) => (
              <PlannedDomainMethodCard key={workflow.id} workflow={workflow} />
            ))}
            {(domain.directContextualWorkflows ?? [])
              .filter((workflow) => workflow.presentation === "card")
              .map((workflow) => (
                <ContextualDomainMethodCard key={workflow.id} workflow={workflow} />
              ))}
          </div>
          {domain.contextualSummaryKey !== undefined ? (
            <p className="analysis-domain-contextual-summary">
              {t(domain.contextualSummaryKey)}
            </p>
          ) : null}
        </>
      ) : (
        <div className="analysis-domain-family-grid">
          {domain.families.map((family) => (
            <AnalysisDomainFamilyCard
              catalog={catalog}
              family={family}
              key={family.id}
              selectedMethodId={selectedMethodId}
              onSelectMethod={onSelectMethod}
            />
          ))}
        </div>
      )}
    </section>
  );
}
