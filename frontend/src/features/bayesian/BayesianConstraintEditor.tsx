import { Plus, Trash2 } from "lucide-react";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { mixedMessages } from "../../i18n/boMixed";
import { datasetImportMessages } from "../../i18n/boDatasetImport";
import type { AppLocale } from "../../i18n/types";
import type { MixedConstraintDraft, MixedFactorDraft } from "./boMixedDraft";

interface Props {
  locale: AppLocale; factors: readonly MixedFactorDraft[]; constraints: MixedConstraintDraft[]; idPrefix?: string;
  onChange: (update: (current: MixedConstraintDraft[]) => MixedConstraintDraft[]) => void;
  onAdd: () => void;
}
export function BayesianConstraintEditor({ locale, factors, constraints, onChange, onAdd, idPrefix = "bo-mixed" }: Props) {
  const text = mixedMessages(locale);
  const invalidNumber = datasetImportMessages(locale).invalidNumber;
  const numeric = factors.filter(row => row.kind === "continuous" || row.kind === "discrete_numeric");
  function update(key: number, values: Partial<MixedConstraintDraft>) { onChange(current => current.map(row => row.key === key ? { ...row, ...values } : row)); }
  return <fieldset className="bo-planning-fieldset"><legend>{text.constraints}</legend><p>{text.constraintMeaning}</p>
    {constraints.map(row => {
      const identity = `constraint_${row.key}`;
      const boundError = `${idPrefix}-${identity}-bound-error`;
      const invalidBound = parseDoeResponseNumber(row.bound) === null;
      return <div key={row.key} className="bo-planning-fields form-grid">
        <label>{text.constraintName}<input aria-label={`${text.constraintName} ${identity}`} value={row.name} maxLength={80} onChange={event => { const value = event.currentTarget.value; update(row.key, { name: value }); }} /></label>
        {numeric.map(factor => {
          const value = row.coefficients[factor.factorId] ?? "", invalid = value.trim() !== "" && parseDoeResponseNumber(value) === null;
          const label = `${text.coefficient} ${identity} ${factor.factorId}`;
          const errorId = `${idPrefix}-${identity}-${factor.factorId}-error`;
          return <label key={factor.factorId}>{factor.name}: {text.coefficient}<input inputMode="decimal" aria-label={label} aria-invalid={invalid || undefined} aria-describedby={invalid ? errorId : undefined} value={value}
            onChange={event => { const value = event.currentTarget.value; onChange(current => current.map(item => item.key === row.key ? { ...item, coefficients: { ...item.coefficients, [factor.factorId]: value } } : item)); }} />{invalid && <span id={errorId}>{invalidNumber}</span>}</label>;
        })}
        <label>{text.relation}<select aria-label={`${text.relation} ${identity}`} value={row.relation} onChange={event => { const value = event.currentTarget.value as MixedConstraintDraft["relation"]; update(row.key, { relation: value }); }}><option value="less_than_or_equal">≤</option><option value="greater_than_or_equal">≥</option></select></label>
        <label>{text.bound}<input inputMode="decimal" aria-label={`${text.bound} ${identity}`} aria-invalid={invalidBound || undefined} aria-describedby={invalidBound ? boundError : undefined} value={row.bound} onChange={event => { const value = event.currentTarget.value; update(row.key, { bound: value }); }} />{invalidBound && <span id={boundError}>{invalidNumber}</span>}</label>
        <button type="button" className="secondary-button" aria-label={`${text.removeConstraint} ${identity}`} onClick={() => onChange(current => current.filter(item => item.key !== row.key))}><Trash2 size={16} aria-hidden="true" />{text.removeConstraint}</button>
      </div>;
    })}
    <button type="button" className="secondary-button" disabled={constraints.length >= 16 || numeric.length === 0} onClick={onAdd}><Plus size={16} aria-hidden="true" />{text.addConstraint}</button>
  </fieldset>;
}
