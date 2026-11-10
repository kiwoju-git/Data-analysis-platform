import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Plus, Save, Trash2, X } from "lucide-react";
import { createMixedStudy } from "../../api/boMixed";
import { ApiRequestError } from "../../api/client";
import type { MixedCorrelationPolicy, MixedStudyResponse } from "../../api/types/boMixed";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixedCorrelationLabel, mixedMessages } from "../../i18n/boMixed";
import { augmentationFailureCode } from "./boAugmentationDraft";
import { createPlanningRequestFence } from "./boPlanningDraft";
import { buildMixedStudyRequest, newMixedFactor, validMixedStudy, type MixedConstraintDraft, type MixedFactorDraft } from "./boMixedDraft";
import { buildVectorObjective, newResponseDraft, type ResponseGoalDraft } from "./bayesianVectorDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import { BayesianResponseGoals } from "./BayesianResponseGoals";
import "./boPlanning.css";

interface Props { ownerKey: string; disabled: boolean; onCreated: (study: MixedStudyResponse) => void; onCancel: () => void; onBusyChange: (busy: boolean) => void }
export function BayesianMixedStudyBuilder({ ownerKey, disabled, onCreated, onCancel, onBusyChange }: Props) {
  const { locale } = useI18n(), text = mixedMessages(locale);
  const [name, setName] = useState(""), [objectiveName, setObjectiveName] = useState("Desirability"), [seed, setSeed] = useState("42"), [size, setSize] = useState("8");
  const [factors, setFactors] = useState(() => [newMixedFactor(1), newMixedFactor(2, "nominal")]);
  const [constraints, setConstraints] = useState<MixedConstraintDraft[]>([]), [goals, setGoals] = useState(() => [newResponseDraft(1)]);
  const nextFactor = useRef(3), nextConstraint = useRef(1), nextResponse = useRef(2);
  const [creating, setCreating] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState<string | null>(null);
  const guard = useRef(createPlanningRequestFence()).current; guard.source(ownerKey);
  const running = useRef(false), createdCallback = useRef(onCreated); createdCallback.current = onCreated;
  useEffect(() => () => guard.invalidate(), [guard]);
  useEffect(() => { running.current = false; setCreating(false); setUncertain(false); setError(null); }, [ownerKey]);
  useEffect(() => { onBusyChange(creating); return () => onBusyChange(false); }, [creating, onBusyChange]);
  const goalEditor = { responseGoals: goals,
    updateResponseGoal: <Field extends keyof Omit<ResponseGoalDraft, "key">>(key: number, field: Field, value: ResponseGoalDraft[Field]) => setGoals(current => current.map(row => row.key === key ? { ...row, [field]: value } : row)),
    addResponseGoal: () => { const next = newResponseDraft(nextResponse.current++); setGoals(current => current.length < 4 ? [...current, next] : current); },
    removeResponseGoal: (key: number) => setGoals(current => current.length > 1 ? current.filter(row => row.key !== key) : current),
  };
  function changeFactor<Field extends keyof Omit<MixedFactorDraft, "key">>(key: number, field: Field, value: MixedFactorDraft[Field]) { setError(null); setFactors(current => current.map(row => row.key === key ? { ...row, [field]: value } : row)); }
  function moveLevel(factor: MixedFactorDraft, index: number, delta: number) {
    if (index + delta < 0 || index + delta >= factor.levels.length) return;
    const levels = [...factor.levels]; [levels[index], levels[index + delta]] = [levels[index + delta], levels[index]]; changeFactor(factor.key, "levels", levels);
  }
  async function submit() {
    if (disabled || running.current || uncertain) return;
    const objective = buildVectorObjective(objectiveName, goals);
    const request = typeof objective === "string" ? objective : buildMixedStudyRequest({ name, factors, constraints, objective, seed, size });
    if (typeof request === "string") { setError(request); return; }
    const token = guard.begin(); running.current = true; setCreating(true); setError(null);
    try {
      const result = await createMixedStudy(request);
      if (!guard.current(token)) return;
      if (!validMixedStudy(result) || !sameDesirabilityJson(result.objective, request.objective) || result.factors.length !== request.factors.length ||
        request.factors.some((factor, index) => Object.entries(factor).some(([key, value]) => !sameDesirabilityJson(value, result.factors[index][key as keyof typeof factor])))) throw new Error("bayesian_mixed_source_mismatch");
      createdCallback.current(result);
    } catch (caught) { if (guard.current(token)) { setError(augmentationFailureCode(caught)); setUncertain(!(caught instanceof ApiRequestError && caught.status >= 400 && caught.status < 500)); } }
    finally { if (guard.current(token)) { running.current = false; setCreating(false); } }
  }
  const numeric = factors.filter(row => row.kind === "continuous" || row.kind === "discrete_numeric");
  return <section className="bo-planning" aria-label={text.title}><h3>{text.title}</h3><p>{text.categoryMeaning}</p><p>{text.parity}</p>
    <fieldset className="bo-planning-confirm-lock" disabled={disabled || creating || uncertain}>
      <div className="bo-planning-fields"><label>{text.name}<input value={name} maxLength={120} onChange={event => setName(event.currentTarget.value)} /></label><label>{text.objective}<input value={objectiveName} maxLength={80} onChange={event => setObjectiveName(event.currentTarget.value)} /></label></div>
      <h4>{text.factors}</h4><p>{text.parameterLimits}</p>
      {factors.map((factor, index) => <fieldset key={factor.key} className="bo-planning-fieldset"><legend>{text.factor} {index + 1}</legend>
        <div className="bo-planning-fields"><label>{text.factorId}<input value={factor.factorId} disabled={constraints.length > 0} maxLength={64} onChange={event => changeFactor(factor.key, "factorId", event.currentTarget.value)} /></label>
          <label>{text.factorName}<input value={factor.name} maxLength={80} onChange={event => changeFactor(factor.key, "name", event.currentTarget.value)} /></label>
          <label>{text.unit}<input value={factor.unit} maxLength={40} onChange={event => changeFactor(factor.key, "unit", event.currentTarget.value)} /></label>
          <label>{text.kind}<select aria-label={text.kind} value={factor.kind} disabled={constraints.length > 0} onChange={event => changeFactor(factor.key, "kind", event.currentTarget.value as MixedFactorDraft["kind"])}>
            <option value="continuous">{text.continuous}</option><option value="discrete_numeric">{text.discrete}</option><option value="nominal">{text.nominal}</option><option value="ordinal">{text.ordinal}</option></select></label>
          {factor.kind === "continuous" || factor.kind === "discrete_numeric" ? <>{([ ["low", text.low], ["high", text.high], ...(factor.kind === "discrete_numeric" ? [["step", text.step] as const] : []), ["decimals", text.decimals] ] as const).map(([field, label]) => <label key={field}>{label}<input inputMode="decimal" value={factor[field]} onChange={event => changeFactor(factor.key, field, event.currentTarget.value)} /></label>)}</> :
            <label>{text.correlation}<select aria-label={text.correlation} value={factor.correlation} onChange={event => changeFactor(factor.key, "correlation", event.currentTarget.value as MixedCorrelationPolicy)}>
              {(["equal_positive_correlation_v1", "unequal_hyperspherical_correlation_v1", ...(factor.kind === "ordinal" ? ["ordinal_monotone_latent_rbf_v1"] : [])] as MixedCorrelationPolicy[]).map(policy => <option key={policy} value={policy}>{mixedCorrelationLabel(policy, locale)}</option>)}
            </select></label>}
        </div>
        {(factor.kind === "nominal" || factor.kind === "ordinal") && <><p>{factor.kind === "ordinal" ? text.ordinalMeaning : text.categoryMeaning}</p><ol className="bo-mixed-levels">{factor.levels.map((level, levelIndex) => <li key={levelIndex}>
          <input aria-label={`${factor.name}: ${text.levels} ${levelIndex + 1}`} value={level} maxLength={1024} onChange={event => { const value = event.currentTarget.value; changeFactor(factor.key, "levels", factor.levels.map((old, i) => i === levelIndex ? value : old)); }} />
          <button type="button" className="secondary-button bo-planning-icon" aria-label={text.up} title={text.up} disabled={levelIndex === 0} onClick={() => moveLevel(factor, levelIndex, -1)}><ArrowUp size={16} aria-hidden="true" /></button>
          <button type="button" className="secondary-button bo-planning-icon" aria-label={text.down} title={text.down} disabled={levelIndex === factor.levels.length - 1} onClick={() => moveLevel(factor, levelIndex, 1)}><ArrowDown size={16} aria-hidden="true" /></button>
          <button type="button" className="secondary-button bo-planning-icon" aria-label={text.removeLevel} title={text.removeLevel} disabled={factor.levels.length <= 2} onClick={() => changeFactor(factor.key, "levels", factor.levels.filter((_, i) => i !== levelIndex))}><Trash2 size={16} aria-hidden="true" /></button>
        </li>)}</ol><button type="button" className="secondary-button" disabled={factor.levels.length >= 32} onClick={() => changeFactor(factor.key, "levels", [...factor.levels, ""])}><Plus size={16} aria-hidden="true" />{text.addLevel}</button></>}
        <button type="button" className="secondary-button" disabled={factors.length <= 1 || constraints.length > 0} onClick={() => setFactors(current => current.filter(row => row.key !== factor.key))}><Trash2 size={16} aria-hidden="true" />{text.removeFactor}</button>
      </fieldset>)}
      <button type="button" className="secondary-button" disabled={factors.length >= 10} onClick={() => { const factor = newMixedFactor(nextFactor.current++); setFactors(current => [...current, factor]); }}><Plus size={16} aria-hidden="true" />{text.addFactor}</button>
      <BayesianResponseGoals draft={goalEditor} sourceKey={JSON.stringify([ownerKey, name, factors, goals])} />
      <fieldset className="bo-planning-fieldset"><legend>{text.constraints}</legend><p>{text.constraintMeaning}</p>{constraints.map(row => <div key={row.key} className="bo-planning-fields">
        <label>{text.constraintName}<input value={row.name} onChange={event => { const value = event.currentTarget.value; setConstraints(current => current.map(item => item.key === row.key ? { ...item, name: value } : item)); }} /></label>
        {numeric.map(factor => <label key={factor.factorId}>{factor.name}: {text.coefficient}<input inputMode="decimal" value={row.coefficients[factor.factorId] ?? ""} onChange={event => { const value = event.currentTarget.value; setConstraints(current => current.map(item => item.key === row.key ? { ...item, coefficients: { ...item.coefficients, [factor.factorId]: value } } : item)); }} /></label>)}
        <label>{text.relation}<select aria-label={text.relation} value={row.relation} onChange={event => { const value = event.currentTarget.value as MixedConstraintDraft["relation"]; setConstraints(current => current.map(item => item.key === row.key ? { ...item, relation: value } : item)); }}><option value="less_than_or_equal">≤</option><option value="greater_than_or_equal">≥</option></select></label>
        <label>{text.bound}<input inputMode="decimal" value={row.bound} onChange={event => { const value = event.currentTarget.value; setConstraints(current => current.map(item => item.key === row.key ? { ...item, bound: value } : item)); }} /></label>
        <button type="button" className="secondary-button" onClick={() => setConstraints(current => current.filter(item => item.key !== row.key))}><Trash2 size={16} aria-hidden="true" />{text.removeConstraint}</button>
      </div>)}<button type="button" className="secondary-button" disabled={constraints.length >= 16 || numeric.length === 0} onClick={() => { const key = nextConstraint.current++; setConstraints(current => [...current, { key, name: `Constraint ${key}`, relation: "less_than_or_equal", bound: "", coefficients: {} }]); }}><Plus size={16} aria-hidden="true" />{text.addConstraint}</button></fieldset>
      <div className="bo-planning-fields"><label>{text.seed}<input inputMode="numeric" value={seed} onChange={event => setSeed(event.currentTarget.value)} /></label><label>{text.size}<input inputMode="numeric" value={size} onChange={event => setSize(event.currentTarget.value)} /></label></div><p>{text.initialPolicy}</p>
      <button type="button" className="primary-button" onClick={() => void submit()}><Save size={16} aria-hidden="true" />{text.create}</button>
    </fieldset>
    {creating && <p role="status">{text.working}</p>}{error && <div className="notice-box notice-warning" role="alert"><p>{uncertain ? text.uncertainCreate : text.invalid}</p><code>{error}</code></div>}
    <button type="button" className="secondary-button" disabled={creating} onClick={onCancel}><X size={16} aria-hidden="true" />{text.cancel}</button>
  </section>;
}
