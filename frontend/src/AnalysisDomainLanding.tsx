import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import { ANALYSIS_DOMAINS, type AnalysisDomainDefinition } from "./analysisDomains";
import {
  domainCatalogMethods,
  validateAnalysisDomainCatalog,
} from "./analysisDomainMapping";
import { domainGuidanceKey } from "./analysisDomainGuidance";
import { AnalysisDomainFamilyCard } from "./AnalysisDomainFamilyCard";
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
              0,
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
      </div>
      {mappingNotice}
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
    </section>
  );
}
