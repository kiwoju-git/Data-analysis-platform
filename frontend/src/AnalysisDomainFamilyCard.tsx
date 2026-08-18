import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import type { AnalysisDomainFamily } from "./analysisDomains";
import {
  contextualCatalogMethods,
  familyCatalogMethods,
} from "./analysisDomainMapping";
import { methodLabel } from "./i18n/catalogLabels";
import { useI18n } from "./i18n/LocaleProvider";

interface AnalysisDomainFamilyCardProps {
  catalog: AnalysisMethodListResponse;
  family: AnalysisDomainFamily;
  selectedMethodId: string | null;
  onSelectMethod: (method: AnalysisMethodDescriptor) => void;
}
export function AnalysisDomainFamilyCard({
  catalog,
  family,
  selectedMethodId,
  onSelectMethod,
}: AnalysisDomainFamilyCardProps) {
  const { locale, t } = useI18n();
  const methods = familyCatalogMethods(catalog, family);
  const contextualMethods = contextualCatalogMethods(catalog, family);

  return (
    <section className="analysis-domain-family-card">
      <div className="analysis-domain-family-heading">
        <div>
          <h3>{t(family.labelKey)}</h3>
          <p>{t(family.descriptionKey)}</p>
        </div>
        <span className="analysis-domain-count">
          {t("analysisDomains.availableCount", {
            count: methods.filter((method) => method.availability === "available").length,
          })}
        </span>
      </div>
      {methods.length > 0 ? (
        <div className="analysis-domain-method-list">
          {methods.map((method) => (
            <button
              aria-pressed={selectedMethodId === method.method_id}
              className={selectedMethodId === method.method_id ? "is-active" : ""}
              disabled={method.availability !== "available"}
              key={method.method_id}
              onClick={() => onSelectMethod(method)}
              type="button"
            >
              {methodLabel(method, locale)}
            </button>
          ))}
        </div>
      ) : null}
      {contextualMethods.map((method) => (
        <div className="analysis-domain-workflow-row" key={method.method_id}>
          <span>{methodLabel(method, locale)}</span>
          <small>{t("analysisContext.label")}</small>
        </div>
      ))}
      {(family.contextualWorkflows ?? []).map((workflow) => (
        <div className="analysis-domain-workflow-row" key={workflow.id}>
          <span>
            <strong>{t(workflow.labelKey)}</strong>
            {" "}
            {t(workflow.descriptionKey)}
          </span>
          <small>{t("analysisContext.label")}</small>
        </div>
      ))}
      {(family.plannedWorkflows ?? []).map((workflow) => (
        <div className="analysis-domain-workflow-row is-planned" key={workflow.id}>
          <span>
            <strong>{t(workflow.labelKey)}</strong>
            {" "}
            {t(workflow.descriptionKey)}
          </span>
          <small>{t("analysisPlanned.label")}</small>
        </div>
      ))}
    </section>
  );
}
