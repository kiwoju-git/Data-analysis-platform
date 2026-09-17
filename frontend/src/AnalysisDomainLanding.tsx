import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import type { AnalysisDomainDefinition } from "./analysisDomains";
import { AnalysisDomainGrid } from "./AnalysisDomainGrid";
import {
  landingCatalogMethods,
  contextualCatalogMethods,
  validateAnalysisDomainCatalog,
} from "./analysisDomainMapping";
import { domainGuidanceKey } from "./analysisDomainGuidance";
import { methodLabel } from "./i18n/catalogLabels";
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
  const { locale, t } = useI18n();
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
        <AnalysisDomainGrid catalog={catalog} onOpenDomain={onOpenDomain} />
      </section>
    );
  }

  const entries = landingCatalogMethods(catalog, domain);
  const grouped = domain.id === "mean-equivalence";
  const methodCard = ({ method, family }: (typeof entries)[number]) => (
    <AnalysisDomainMethodCard
      key={method.method_id}
      familyLabel={grouped || family === null ? undefined : t(family.labelKey)}
      method={method}
      selected={selectedMethodId === method.method_id}
      onSelectMethod={onSelectMethod}
    />
  );

  return (
    <section className="analysis-domain-landing" aria-label={t(domain.labelKey)}>
      {mappingNotice}
      {grouped ? (
        <div className="analysis-method-groups">
          {domain.families.map((family) => {
            const methods = entries.filter((entry) => entry.family?.id === family.id);
            if (methods.length === 0) return null;
            const headingId = `analysis-method-group-${family.id}`;
            return (
              <section className="analysis-method-group" key={family.id}
                aria-labelledby={headingId} data-family-id={family.id}>
                <h3 id={headingId}>{t(family.labelKey)}</h3>
                <div className="analysis-domain-method-grid">{methods.map(methodCard)}</div>
              </section>
            );
          })}
        </div>
      ) : (
        <div className="analysis-domain-method-grid">
          {entries.map(methodCard)}
          {(domain.directPlannedWorkflows ?? []).map((workflow) => (
            <PlannedDomainMethodCard key={workflow.id} workflow={workflow} />
          ))}
          {(domain.directContextualWorkflows ?? [])
            .filter((workflow) => workflow.presentation === "card")
            .map((workflow) => (
              <ContextualDomainMethodCard key={workflow.id} workflow={workflow} />
            ))}
        </div>
      )}
      {domain.contextualSummaryKey !== undefined ? (
        <p className="analysis-domain-contextual-summary">
          {t(domain.contextualSummaryKey)}
        </p>
      ) : null}
      <details className="analysis-domain-guide">
        <summary>{t("domain.compactGuide")}</summary>
        <p>{t(domainGuidanceKey(domain.id))}</p>
        {(domain.selectionGuideKeys?.length ?? 0) > 0 ? <ul>
          {domain.selectionGuideKeys?.map((key) => <li key={key}>{t(key)}</li>)}
        </ul> : null}
      </details>
      {domain.families.map((family) => <div className="analysis-domain-supporting-items" key={family.id}>
        {contextualCatalogMethods(catalog, family).map((method) =>
          <div className="analysis-domain-workflow-row" key={method.method_id}>
            <span>{methodLabel(method, locale)}</span><small>{t("analysisContext.label")}</small>
          </div>)}
        {(family.contextualWorkflows ?? []).map((workflow) =>
          <div className="analysis-domain-workflow-row" key={workflow.id}>
            <span>{t(workflow.labelKey)}</span><small>{t(workflow.statusKey ?? "analysisContext.label")}</small>
          </div>)}
        {(family.plannedWorkflows ?? []).map((workflow) =>
          <div className="analysis-domain-workflow-row is-planned" key={workflow.id}>
            <span>{t(workflow.labelKey)}</span><small>{t("analysisPlanned.label")}</small>
          </div>)}
      </div>)}
    </section>
  );
}
