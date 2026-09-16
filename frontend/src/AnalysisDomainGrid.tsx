import type { AnalysisMethodListResponse } from "./api";
import { ANALYSIS_DOMAINS, type AnalysisDomainDefinition } from "./analysisDomains";
import { domainCatalogMethods } from "./analysisDomainMapping";
import { NavigationIcon } from "./components/NavigationIcon";
import { useI18n } from "./i18n/LocaleProvider";
import { methodLabel } from "./i18n/catalogLabels";
import type { TranslationKey } from "./i18n/translate";

const purposeKeys: Record<AnalysisDomainDefinition["id"], TranslationKey> = {
  "basic-exploration": "dashboard.domain.basic",
  "mean-equivalence": "dashboard.domain.mean",
  "proportions-categorical": "dashboard.domain.categorical",
  "correlation-regression-prediction": "dashboard.domain.regression",
  "doe-optimization": "dashboard.domain.doe",
  "ai-ml-experimental-design": "dashboard.domain.ai",
  "quality-process-monitoring": "dashboard.domain.quality",
  "measurement-variability": "dashboard.domain.measurement",
};

export function AnalysisDomainGrid({ catalog, onOpenDomain, compact = false }: {
  catalog: AnalysisMethodListResponse | null;
  onOpenDomain: (domain: AnalysisDomainDefinition) => void;
  compact?: boolean;
}) {
  const { t, locale } = useI18n();
  return <div className={`analysis-domain-grid${compact ? " is-compact" : ""}`}>
    {ANALYSIS_DOMAINS.map((domain) => {
      const methods = catalog === null ? [] : domainCatalogMethods(catalog, domain);
      return <button className="analysis-domain-card" key={domain.id}
        onClick={() => onOpenDomain(domain)} type="button">
        <span className="navigation-card-top"><NavigationIcon name={domain.id} size={24} />
          <NavigationIcon name="arrow" className="navigation-card-arrow" size={16} /></span>
        <strong>{t(domain.labelKey)}</strong>
        <span className="analysis-domain-card-description">{t(purposeKeys[domain.id])}</span>
        {!compact ? <span className="analysis-domain-card-families">
          {domain.landingMode === "flat_methods"
            ? methods.slice(0, 3).map((method) => methodLabel(method, locale)).join(" · ")
            : domain.families.slice(0, 3).map((family) => t(family.labelKey)).join(" · ")}
        </span> : null}
      </button>;
    })}
  </div>;
}
