import type { MixedCorrelationPolicy } from "../../api/types/boMixed";
import { datasetImportMessages } from "../../i18n/boDatasetImport";
import { mixedCorrelationLabel, mixedMessages } from "../../i18n/boMixed";
import type { AppLocale } from "../../i18n/types";
import type { MixedFactorDraft } from "./boMixedDraft";

interface Props { locale: AppLocale; factor: MixedFactorDraft; label: string; onChange: (policy: MixedCorrelationPolicy) => void }
export function BayesianCategoryCorrelationEditor({ locale, factor, label, onChange }: Props) {
  const text = mixedMessages(locale), importText = datasetImportMessages(locale);
  const incompatible = factor.kind === "nominal" && factor.correlation === "ordinal_monotone_latent_rbf_v1";
  const overLimit = factor.correlation === "unequal_hyperspherical_correlation_v1" && factor.levels.length > 8;
  const invalid = incompatible || overLimit;
  const id = `bo-import-policy-${factor.factorId}`;
  return <label>{label}<select aria-label={label} aria-invalid={invalid || undefined} aria-describedby={invalid ? id : undefined} value={factor.correlation} onChange={event => { const value = event.currentTarget.value as MixedCorrelationPolicy; onChange(value); }}>
    {(["equal_positive_correlation_v1", "unequal_hyperspherical_correlation_v1", ...(factor.kind === "ordinal" ? ["ordinal_monotone_latent_rbf_v1"] : [])] as MixedCorrelationPolicy[]).map(policy => <option key={policy} value={policy}>{mixedCorrelationLabel(policy, locale)}</option>)}
    {incompatible && <option value="ordinal_monotone_latent_rbf_v1" disabled>{text.latent}</option>}
  </select>{invalid && <span id={id} role="alert">{incompatible ? importText.incompatiblePolicy : text.parameterLimits}</span>}</label>;
}
