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
import { methodLabel } from "./i18n/catalogLabels";

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
  const { t, locale } = useI18n();
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
            return (
              <button
                className="analysis-domain-card"
                key={candidate.id}
                onClick={() => onOpenDomain(candidate)}
                type="button"
              >
                <strong>{t(candidate.labelKey)}</strong>
                <span className="analysis-domain-card-description">
                  {t(candidate.descriptionKey)}
                </span>
                <span className="analysis-domain-card-families">
                  {candidate.landingMode === "flat_methods"
                    ? methods.slice(0, 3).map((method) => methodLabel(method, locale)).join(" · ")
                    : candidate.families.slice(0, 3).map((family) => t(family.labelKey)).join(" · ")}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    );
  }

  return (
    <section className="analysis-domain-landing" aria-label={t(domain.labelKey)}>
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
          {domain.families.filter((family) => family.methodIds.length > 0).map((family) => (
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
      <details className="analysis-domain-guide">
        <summary>{t("domain.compactGuide")}</summary>
        <p>{t(domainGuidanceKey(domain.id))}</p>
        {(domain.selectionGuideKeys?.length ?? 0) > 0 ? <ul>
          {domain.selectionGuideKeys?.map((key) => <li key={key}>{t(key)}</li>)}
        </ul> : null}
      </details>
      {domain.landingMode === "family_cards" ? domain.families.filter((family) => family.methodIds.length === 0).map((family) =>
        <AnalysisDomainFamilyCard key={family.id} family={family} catalog={catalog}
          selectedMethodId={selectedMethodId} onSelectMethod={onSelectMethod} />) : null}
    </section>
  );
}
