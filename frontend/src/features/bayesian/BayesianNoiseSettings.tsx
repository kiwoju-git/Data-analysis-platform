import type { BayesianStudyResponse } from "../../api";
import { DoeSettingsTable } from "../../doe/DoeSettingsTable";
import { useI18n } from "../../i18n/LocaleProvider";
import { boText, buildNoisePolicy, noiseInputError, type BayesianNoiseDraft } from "./boNoisePolicy";

export function BayesianNoiseSettings({ study, draft, disabled, onChange }: {
  study: BayesianStudyResponse; draft: BayesianNoiseDraft; disabled: boolean;
  onChange: (draft: BayesianNoiseDraft) => void;
}) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const errors = buildNoisePolicy(draft, study.factors).errors;
  function numeric(key: "noiseInitial" | "noiseLower" | "noiseUpper" | "fixedNoiseSd" | "sampleCount" | "minBatchDistance", label: string) {
    const id = `bo-policy-${key}`;
    return { key, label, controlId: id, control: <input id={id} inputMode={key === "sampleCount" ? "numeric" : "decimal"}
      value={draft[key]} disabled={disabled} aria-invalid={Boolean(errors[key])} aria-describedby={errors[key] ? `${id}-error` : undefined}
      onChange={event => onChange({ ...draft, [key]: event.currentTarget.value })} />,
      helper: errors[key] ? <span id={`${id}-error`} className="error-text">{noiseInputError(errors[key], locale)}</span> : undefined };
  }
  return <section aria-label={text("노이즈와 관측 처리", "Noise and observation policy")}>
    <DoeSettingsTable ariaLabel={text("노이즈와 관측 처리 설정", "Noise and observation settings")} fields={[
      { key: "noise", label: text("측정 노이즈", "Measurement noise"), controlId: "bo-noise-mode",
        control: <select id="bo-noise-mode" value={draft.noiseMode} disabled={disabled} onChange={event => onChange({ ...draft, noiseMode: event.currentTarget.value as BayesianNoiseDraft["noiseMode"] })}>
          <option value="estimate">{text("분산 추정", "Estimate variance")}</option>
          <option value="fixed">{text("측정 SD 지정", "Fixed measurement SD")}</option>
          <option value="near_noiseless">{text("거의 무잡음", "Near-noiseless")}</option>
        </select>, helper: text("Jitter는 수치 안정화이며 측정오차 SD가 아닙니다.", "Jitter stabilizes numerical computation; it is not measurement SD.") },
      ...(draft.noiseMode === "fixed" ? [numeric("fixedNoiseSd", `${text("측정 SD", "Measurement SD")} (${study.objective.unit ?? text("반응 원단위", "response units")})`)] : []),
      { key: "observations", label: text("반복 관측 처리", "Replicate observations"), controlId: "bo-observation-policy",
        control: <select id="bo-observation-policy" value={draft.observationMode} disabled={disabled} onChange={event => onChange({ ...draft, observationMode: event.currentTarget.value as BayesianNoiseDraft["observationMode"] })}>
          <option value="retain_raw">{text("원 관측 유지", "Retain raw observations")}</option>
          <option value="exact_replicates">{text("동일 조건 반복의 정확 집계", "Exact replicate compression")}</option>
          <option value="nearby_diagnostics">{text("근접 조건 진단만", "Nearby diagnostics only")}</option>
        </select>, helper: text("집계는 추천의 학습 표현만 바꿉니다. 원 이력은 보존하며 근접 조건은 합치지 않습니다.", "Compression changes only this fit view. History is preserved; nearby conditions are not merged.") },
    ]} />
    {draft.observationMode === "nearby_diagnostics" ? <DoeSettingsTable ariaLabel={text("근접 진단 허용 거리", "Nearby diagnostic tolerances")} fields={[
      { key: "units", label: text("허용 거리 단위", "Tolerance units"), controlId: "bo-nearby-units",
        control: <select id="bo-nearby-units" disabled={disabled} value={draft.nearbyUnits} onChange={event => onChange({ ...draft, nearbyUnits: event.currentTarget.value as "actual" | "normalized" })}>
          <option value="actual">{text("실제 단위", "Actual units")}</option><option value="normalized">{text("정규화 0~1", "Normalized 0-1")}</option></select> },
      ...study.factors.map((factor, index) => {
        const key = `tolerance:${factor.factor_id}`, id = `bo-tolerance-${index}`;
        return { key, label: `${factor.name}${draft.nearbyUnits === "actual" && factor.unit ? ` (${factor.unit})` : ""}`, controlId: id,
          control: <input id={id} inputMode="decimal" disabled={disabled} value={draft.nearbyTolerances[factor.factor_id] ?? ""}
            aria-invalid={Boolean(errors[key])} aria-describedby={errors[key] ? `${id}-error` : undefined}
            onChange={event => onChange({ ...draft, nearbyTolerances: { ...draft.nearbyTolerances, [factor.factor_id]: event.currentTarget.value } })} />,
          helper: errors[key] ? <span id={`${id}-error`} className="error-text">{noiseInputError(errors[key], locale)}</span> : factor.domain_kind === "discrete_numeric" ? text("이산 인자는 같은 실행 수준끼리만 비교합니다.", "Discrete factors require the same executable level.") : undefined };
      }),
    ]} /> : null}
    <details><summary>{text("노이즈·배치 고급 설정", "Advanced noise and batch settings")}</summary>
      <p className="cell-subtext">{text("노이즈 경계는 표준화 Y의 분산입니다. 기본 상한 1은 물리적 상한이 아닙니다. 미래 한 번의 측정에는 전체 측정 분산을 사용합니다.", "Noise bounds are variances in standardized Y coordinates. The default upper bound 1 is not a physical limit. Future single measurements retain the full observation variance.")}</p>
      <DoeSettingsTable ariaLabel={text("고급 분산과 MC 설정", "Advanced variance and MC settings")} fields={[
        numeric("noiseInitial", text("초기 노이즈 분산", "Initial noise variance")), numeric("noiseLower", text("분산 하한", "Variance lower bound")), numeric("noiseUpper", text("분산 상한", "Variance upper bound")),
        numeric("sampleCount", text("Joint MC 표본 수 (16~256)", "Joint MC samples (16-256)")),
        numeric("minBatchDistance", text("배치 최소 거리 (정규화)", "Minimum batch distance (normalized)")),
      ]} />
      <p className="cell-subtext">{text("단일 후보는 analytic latent EI/ETI입니다. 배치는 plug-in 기준값과 joint latent MC를 사용하며 exact qNEI가 아닙니다. 최소 거리 0은 분산된 배치를 보장하지 않습니다.", "A single candidate uses analytic latent EI/ETI. Batches use a plug-in incumbent and joint latent MC, not exact qNEI. Zero minimum distance does not guarantee dispersed batches.")}</p>
    </details>
  </section>;
}
