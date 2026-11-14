import { useEffect, useRef, useState } from "react";
import { Plus, Save, Trash2, X } from "lucide-react";
import { createMixtureStudy, type MixtureStudy } from "../../api/boMixture";
import { ApiRequestError } from "../../api/client";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixtureMessages } from "../../i18n/boMixture";
import { BayesianResponseGoals } from "./BayesianResponseGoals";
import { BayesianConstraintEditor } from "./BayesianConstraintEditor";
import { BayesianCategoryCorrelationEditor } from "./BayesianCategoryCorrelationEditor";
import { newMixedFactor, type MixedConstraintDraft } from "./boMixedDraft";
import { buildVectorObjective, newResponseDraft, type ResponseGoalDraft } from "./bayesianVectorDraft";
import { buildMixtureGroup, buildMixtureStudyRequest, newMixtureComponent, validMixtureStudy } from "./boMixtureDraft";
import { createPlanningRequestFence } from "./boPlanningDraft";
import { augmentationFailureCode } from "./boAugmentationDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import "./boPlanning.css";

interface Props { ownerKey: string; disabled: boolean; onCreated: (study: MixtureStudy) => void; onCancel: () => void; onBusyChange: (busy: boolean) => void }
export function BayesianMixtureStudyBuilder({ ownerKey, disabled, onCreated, onCancel, onBusyChange }: Props) {
  const { locale } = useI18n(), text = mixtureMessages(locale);
  const [name, setName] = useState(""), [total, setTotal] = useState("1"), [unit, setUnit] = useState("g"), [coding, setCoding] = useState<"lower" | "upper" | "auto">("auto");
  const [components, setComponents] = useState(() => [newMixtureComponent(1), newMixtureComponent(2)]);
  const [process, setProcess] = useState<ReturnType<typeof newMixedFactor>[]>([]);
  const [constraints, setConstraints] = useState<MixedConstraintDraft[]>([]);
  const [goals, setGoals] = useState(() => [newResponseDraft(1)]), [objectiveName, setObjectiveName] = useState("Desirability");
  const [seed, setSeed] = useState("42"), [size, setSize] = useState("8"), [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState<string | null>(null);
  const nextComponent = useRef(3), nextProcess = useRef(1), nextResponse = useRef(2), nextConstraint = useRef(1), running = useRef(false);
  const guard = useRef(createPlanningRequestFence()).current; guard.source(ownerKey);
  useEffect(() => () => guard.invalidate(), [guard]);
  useEffect(() => { onBusyChange(busy); return () => onBusyChange(false); }, [busy, onBusyChange]);
  const group = buildMixtureGroup(total, unit, coding, components);
  const goalEditor = { responseGoals: goals,
    updateResponseGoal: <Field extends keyof Omit<ResponseGoalDraft, "key">>(key: number, field: Field, value: ResponseGoalDraft[Field]) => setGoals(current => current.map(row => row.key === key ? { ...row, [field]: value } : row)),
    addResponseGoal: () => setGoals(current => current.length < 4 ? [...current, newResponseDraft(nextResponse.current++)] : current),
    removeResponseGoal: (key: number) => setGoals(current => current.length > 1 ? current.filter(row => row.key !== key) : current),
  };
  async function submit() {
    if (disabled || running.current || uncertain) return;
    const objective = buildVectorObjective(objectiveName, goals);
    const request = typeof objective === "string" ? objective : buildMixtureStudyRequest({ name, total, unit, coding, components, process, constraints, objective, seed, size });
    if (typeof request === "string") { setError(request); return; }
    const token = guard.begin(); running.current = true; setBusy(true); setError(null);
    try {
      const created = await createMixtureStudy(request);
      if (!guard.current(token)) return;
      if (!validMixtureStudy(created) || !sameDesirabilityJson(created.mixture, request.mixture) || !sameDesirabilityJson(created.process_factors, request.process_factors) || !sameDesirabilityJson(created.constraints, request.constraints) || !sameDesirabilityJson(created.objective, request.objective)) throw Error("bayesian_mixture_source_mismatch");
      onCreated(created);
    } catch (caught) { if (guard.current(token)) { setError(augmentationFailureCode(caught)); setUncertain(!(caught instanceof ApiRequestError && caught.status >= 400 && caught.status < 500)); } }
    finally { if (guard.current(token)) { running.current = false; setBusy(false); } }
  }
  const constraintFactors = [...components.map(c => ({ ...newMixedFactor(c.key), factorId: c.factorId, name: c.name, unit, low: c.low, high: c.high })), ...process];
  return <section className="bo-planning" aria-label={text.title}><h3>{text.title}</h3>
    <fieldset className="bo-planning-confirm-lock" disabled={disabled || busy || uncertain}>
      <div className="bo-planning-fields"><label>{text.name}<input value={name} maxLength={120} onChange={e => setName(e.currentTarget.value)} /></label>
        <label>{text.total}<input inputMode="decimal" value={total} onChange={e => setTotal(e.currentTarget.value)} aria-invalid={typeof group === "string"} /></label>
        <label>{text.unit}<input value={unit} maxLength={40} onChange={e => setUnit(e.currentTarget.value)} /></label>
        <label>{text.coding}<select aria-label={text.coding} value={coding} onChange={e => setCoding(e.currentTarget.value as typeof coding)}>{(["lower", "upper", "auto"] as const).map(value => <option key={value} value={value}>{text[value]}</option>)}</select></label>
      </div><p>{text.closure}</p><h4>{text.components}</h4>
      {components.map((component, index) => <fieldset key={component.key} className="bo-planning-fieldset"><legend>{text.components} {index + 1}</legend><div className="bo-planning-fields">
        {([["factorId", text.factorId], ["name", text.factorName], ["low", text.lower], ["high", text.upper]] as const).map(([field, label]) => <label key={field}>{label}<input value={component[field]} disabled={field === "factorId" && constraints.length > 0} inputMode={field === "low" || field === "high" ? "decimal" : "text"} onChange={e => { const value = e.currentTarget.value; setComponents(current => current.map(row => row.key === component.key ? { ...row, [field]: value } : row)); }} /></label>)}
        <button type="button" className="secondary-button bo-planning-icon" title={text.remove} aria-label={`${text.remove} ${component.name}`} disabled={components.length <= 2 || constraints.length > 0} onClick={() => setComponents(current => current.filter(row => row.key !== component.key))}><Trash2 size={16} aria-hidden="true" /></button>
      </div></fieldset>)}
      <button type="button" className="secondary-button" disabled={components.length >= 8 || components.length + process.length >= 10} onClick={() => setComponents(current => [...current, newMixtureComponent(nextComponent.current++)])}><Plus size={16} aria-hidden="true" />{text.add}</button>
      {typeof group === "string" && <p className="notice-box notice-warning">{text.invalid}</p>}
      <h4>{text.process}</h4>{process.map(factor => <fieldset key={factor.key} className="bo-planning-fieldset"><legend>{factor.name}</legend><div className="bo-planning-fields">
        {([["factorId", text.factorId], ["name", text.factorName], ["unit", text.unit]] as const).map(([field, label]) => <label key={field}>{label}<input value={factor[field]} disabled={field === "factorId" && constraints.length > 0} onChange={e => { const value = e.currentTarget.value; setProcess(current => current.map(row => row.key === factor.key ? { ...row, [field]: value } : row)); }} /></label>)}
        <label>{text.kind}<select aria-label={`${factor.name}: ${text.kind}`} value={factor.kind} disabled={constraints.length > 0} onChange={e => { const kind = e.currentTarget.value as typeof factor.kind; setProcess(current => current.map(row => row.key === factor.key ? { ...row, kind } : row)); }}>{["continuous", "discrete_numeric", "nominal", "ordinal"].map(kind => <option key={kind} value={kind}>{kind}</option>)}</select></label>
        {factor.kind === "nominal" || factor.kind === "ordinal" ? <label>{text.levels}<textarea value={factor.levels.join("\n")} onChange={e => { const levels = e.currentTarget.value.split("\n"); setProcess(current => current.map(row => row.key === factor.key ? { ...row, levels } : row)); }} /></label> : (["low", "high", ...(factor.kind === "discrete_numeric" ? ["step"] : [])] as ("low" | "high" | "step")[]).map(field => <label key={field}>{field}<input inputMode="decimal" value={factor[field]} onChange={e => { const value = e.currentTarget.value; setProcess(current => current.map(row => row.key === factor.key ? { ...row, [field]: value } : row)); }} /></label>)}
        <button type="button" className="secondary-button bo-planning-icon" title={text.remove} aria-label={`${text.remove} ${factor.name}`} disabled={constraints.length > 0} onClick={() => setProcess(current => current.filter(row => row.key !== factor.key))}><Trash2 size={16} aria-hidden="true" /></button>
      </div></fieldset>)}
      <button type="button" className="secondary-button" disabled={process.length >= 8 || process.length + components.length >= 10} onClick={() => { const factor = newMixedFactor(nextProcess.current++); factor.factorId = `process_${factor.key}`; setProcess(current => [...current, factor]); }}><Plus size={16} aria-hidden="true" />{text.addProcess}</button>
      {process.filter(factor => factor.kind === "nominal" || factor.kind === "ordinal").map(factor => <BayesianCategoryCorrelationEditor key={factor.key} locale={locale} factor={factor} label={`${factor.name}: ${locale === "ko" ? "범주 상관" : "Category correlation"}`} onChange={correlation => setProcess(current => current.map(row => row.key === factor.key ? { ...row, correlation } : row))} />)}
      <label>{locale === "ko" ? "목적 이름" : "Objective name"}<input value={objectiveName} maxLength={80} onChange={e => setObjectiveName(e.currentTarget.value)} /></label>
      <BayesianResponseGoals draft={goalEditor} sourceKey={JSON.stringify([ownerKey, components, process, goals])} />
      <BayesianConstraintEditor locale={locale} factors={constraintFactors} constraints={constraints} onChange={setConstraints} onAdd={() => { const key = nextConstraint.current++; setConstraints(current => [...current, { key, name: `Constraint ${key}`, relation: "less_than_or_equal", bound: "", coefficients: {} }]); }} />
      <div className="bo-planning-fields"><label>{text.seed}<input inputMode="numeric" value={seed} onChange={e => setSeed(e.currentTarget.value)} /></label><label>{text.size}<input inputMode="numeric" value={size} onChange={e => setSize(e.currentTarget.value)} /></label></div>
      <button type="button" className="primary-button" onClick={() => void submit()}><Save size={16} aria-hidden="true" />{text.create}</button>
    </fieldset>{busy && <p role="status">{text.working}</p>}{error && <div className="notice-box notice-warning" role="alert"><p>{uncertain ? text.uncertain : text.invalid}</p><code>{error}</code></div>}
    <button type="button" className="secondary-button" disabled={busy} onClick={onCancel}><X size={16} aria-hidden="true" />{text.cancel}</button>
  </section>;
}
