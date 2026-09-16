import type { AnalysisMethodDescriptor } from "./api";
import type {
  AnalysisContextualWorkflow,
  AnalysisPlannedWorkflow,
} from "./analysisDomains";
import { availabilityLabel } from "./analysisWorkbenchUtils";
import { getMethodCardTags } from "./analysisMethodGuidance";
import { methodLabel } from "./i18n/catalogLabels";
import { useI18n } from "./i18n/LocaleProvider";
import { NavigationIcon } from "./components/NavigationIcon";

interface AvailableMethodCardProps {
  method: AnalysisMethodDescriptor;
  selected: boolean;
  onSelectMethod: (method: AnalysisMethodDescriptor) => void;
}

export function AnalysisDomainMethodCard({
  method,
  selected,
  onSelectMethod,
}: AvailableMethodCardProps) {
  const { locale } = useI18n();
  const tags = getMethodCardTags(method.method_id).slice(0, 3);
  const descriptionId = `analysis-domain-method-${safeId(method.method_id)}`;
  return (
    <button
      aria-label={methodLabel(method, locale)}
      aria-describedby={descriptionId}
      aria-pressed={selected}
      className={`analysis-domain-method-card${selected ? " is-active" : ""}`}
      disabled={method.availability !== "available"}
      onClick={() => onSelectMethod(method)}
      type="button"
    >
      <span className="navigation-card-top"><NavigationIcon name={method.method_id} />
        <NavigationIcon name={selected ? "check" : "arrow"} className="navigation-card-arrow" size={16} /></span>
      <strong>{methodLabel(method, locale)}</strong>
      {locale === "ko" && method.label_en !== method.label_ko ? <span className="analysis-method-subtitle">{method.label_en}</span> : null}
      <span className="analysis-method-compact-tags" id={descriptionId}>
        {tags.map((tag, index) => <span key={`${tag.category}-${index}`}>{tag.label}</span>)}
      </span>
      <small>{availabilityLabel(method)}</small>
    </button>
  );
}

export function PlannedDomainMethodCard({
  workflow,
}: {
  workflow: AnalysisPlannedWorkflow;
}) {
  const { t } = useI18n();
  return (
    <article className="analysis-domain-method-card is-planned">
      <strong>{t(workflow.labelKey)}</strong>
      <span>{t(workflow.descriptionKey)}</span>
      <small>{t("analysisPlanned.label")}</small>
    </article>
  );
}

export function ContextualDomainMethodCard({
  workflow,
}: {
  workflow: AnalysisContextualWorkflow;
}) {
  const { t } = useI18n();
  return (
    <article className="analysis-domain-method-card is-contextual">
      <strong>{t(workflow.labelKey)}</strong>
      <span>{t(workflow.descriptionKey)}</span>
      <small>{t(workflow.statusKey ?? "analysisContext.label")}</small>
    </article>
  );
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/gu, "-");
}
