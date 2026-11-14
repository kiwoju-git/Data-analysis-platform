import { useState } from "react";
import { ChartScatter } from "lucide-react";
import type { MixtureModel, MixtureStudy } from "../../api/boMixture";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixtureMessages } from "../../i18n/boMixture";
import { planningMessages } from "../../i18n/boPlanning";
import { useBoDiagnosticView } from "./hooks/useBoDiagnosticView";
import { validMixtureCoordinates } from "./boMixtureDraft";
import { matrixFromReceipt } from "./boSavedViews";
import { BayesianProfileMatrix } from "./BayesianProfileMatrix";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { BoViewSaveAction } from "./BoViewSaveAction";

export function BayesianMixtureDiagnostics({ study, model, disabled }: { study: MixtureStudy; model: MixtureModel; disabled: boolean }) {
  const { locale } = useI18n(), text = mixtureMessages(locale);
  const [draft, setDraft] = useState<Record<string, string>>(() => Object.fromEntries(Object.entries(study.trials[0]?.actual_coordinates ?? {}).map(([id, value]) => [id, String(value)])));
  const key = JSON.stringify([study.study_version_id, model.model_id, model.snapshot_sha256, draft]);
  const profile = useBoDiagnosticView(key);
  const holds: Record<string, number | string> = {};
  for (const factor of study.factors) {
    const raw = draft[factor.factor_id] ?? "";
    const value = factor.domain_kind === "nominal" || factor.domain_kind === "ordinal" ? raw : parseDoeResponseNumber(raw);
    if (value !== null) holds[factor.factor_id] = value;
  }
  const valid = validMixtureCoordinates(holds, study.mixture, study.process_factors);
  return <section className="bo-planning" aria-label={text.holds}><h4>{text.holds}</h4><p>{text.coVary}</p><p>{text.unsupported}</p>
    <p>{planningMessages(locale).matrixBudget}</p><p>{locale === "ko" ? "숫자·성분 축당 최대 21점을 요청하며 범주 축은 선언된 전체 수준을 포함합니다. 고정되거나 보상할 수 없는 축은 명시적으로 표시합니다." : "Request up to 21 points per numeric/component axis and all declared levels for category axes. Fixed or unavailable compensation axes are labeled explicitly."}</p>
    <fieldset disabled={disabled || profile.pending}><div className="bo-planning-fields">{study.factors.map(factor => <label key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}
      {factor.domain_kind === "nominal" || factor.domain_kind === "ordinal" ? <select value={draft[factor.factor_id] ?? ""} onChange={e => { const value = e.currentTarget.value; setDraft(current => ({ ...current, [factor.factor_id]: value })); }}>{factor.levels.map(level => <option key={level} value={level}>{level}</option>)}</select> : <input inputMode="decimal" value={draft[factor.factor_id] ?? ""} onChange={e => { const value = e.currentTarget.value; setDraft(current => ({ ...current, [factor.factor_id]: value })); }} aria-invalid={!valid} />}
    </label>)}</div><button type="button" className="secondary-button" disabled={!valid} onClick={() => void profile.run({ studyId: study.study_id, modelId: model.model_id, modelHash: model.snapshot_sha256, historyHash: model.history_sha256, responseIds: model.objective.responses.map(r => r.response_id), factorIds: study.factors.map(f => f.factor_id) }, { kind: "profiler_matrix", expected_model_sha256: model.snapshot_sha256, expected_history_sha256: model.history_sha256, holds, points_per_axis: 21, time_budget_ms: 120000 })}><ChartScatter size={16} aria-hidden="true" />{text.profile}</button></fieldset>
    {!valid && <p role="alert">{text.closureInvalid}</p>}{profile.pending && <p role="status">{text.working}</p>}{profile.error && <p role="alert">{text.invalid}</p>}
    {profile.receipt?.payload.kind === "profiler_matrix" && <><BayesianProfileMatrix view={matrixFromReceipt(profile.receipt)} /><BoViewSaveAction receipt={profile.receipt} /></>}
    <BayesianLooPanel studyId={study.study_id} model={model} contextKey={study.study_version_id} disabled={disabled || profile.pending} />
  </section>;
}
