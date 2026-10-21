import type { BayesianStudyResponse } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { DoeSettingsTable } from "../../doe/DoeSettingsTable";
import { boText, strictBoNumber } from "./boNoisePolicy";
import { coordinateText } from "./bayesianDisplay";
import type { useBayesianReplicateState } from "./hooks/useBayesianReplicateState";

export function BayesianReplicatePanel({ study, state, disabled, totalBudget, onSubmit, onRefresh }: {
  study: BayesianStudyResponse; state: ReturnType<typeof useBayesianReplicateState>;
  disabled: boolean; totalBudget: string; onSubmit: (retry?: boolean) => void; onRefresh: () => void;
}) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const completed = study.trials.filter(trial => trial.state === "completed");
  const pending = study.trials.some(trial => trial.state === "pending");
  const count = strictBoNumber(state.count), budget = strictBoNumber(totalBudget);
  const validCount = count !== null && Number.isInteger(count) && count >= 1 && count <= 8;
  const withinBudget = validCount && budget !== null && study.trials.length + count <= budget;
  const locked = disabled || pending || state.canRetry;
  return <section aria-labelledby="bo-replicates-title">
    <h4 id="bo-replicates-title">{text("명시적 반복 실험", "Explicit replicate experiments")}</h4>
    <p>{text("완료한 조건을 그대로 다시 실험합니다. 원 관측값은 바꾸지 않고 새 pending trial마다 실제 측정값을 입력합니다.", "Repeat an exact completed condition. The original observation stays unchanged; enter a separate actual measurement for each new pending trial.")}</p>
    {pending ? <p className="notice-box">{text("현재 pending 실험을 모두 완료하거나 포기한 뒤 반복을 등록할 수 있습니다.", "Complete or abandon every pending trial before registering replicates.")}</p> : null}
    <DoeSettingsTable ariaLabel={text("반복 실험 설정", "Replicate settings")} fields={[
      { key: "parent", label: text("완료한 원 실험", "Completed parent trial"), controlId: "bo-replicate-parent",
        control: <select id="bo-replicate-parent" value={state.parentId} disabled={locked} onChange={event => state.setParentId(event.currentTarget.value)}>
          <option value="">{text("실험 선택", "Select trial")}</option>
          {completed.map(trial => <option key={trial.trial_id} value={trial.trial_id}>Trial {trial.trial_number}: {coordinateText(trial.actual_coordinates)}</option>)}
        </select> },
      { key: "count", label: text("추가 반복 수 (1~8)", "Additional replicates (1-8)"), controlId: "bo-replicate-count",
        control: <input id="bo-replicate-count" value={state.count} inputMode="numeric" disabled={locked} aria-invalid={!validCount || !withinBudget} aria-describedby="bo-replicate-budget" onChange={event => state.setCount(event.currentTarget.value)} />,
        helper: <span id="bo-replicate-budget">{text(`현재 ${study.trials.length} trial / 총 예산 ${totalBudget}`, `Current ${study.trials.length} trials / total budget ${totalBudget}`)}{!validCount || !withinBudget ? ` · ${text("정수 범위와 총 예산을 확인하세요.", "Check the integer range and total budget.")}` : ""}</span> },
    ]} />
    <label className="checkbox-label"><input type="checkbox" checked={state.confirmed} disabled={locked} onChange={event => state.setConfirmed(event.currentTarget.checked)} />{text("같은 조건의 독립적인 추가 실험을 의도했음을 확인합니다.", "I intend to perform additional independent experiments at this exact condition.")}</label>
    <div className="button-row">
      <button type="button" className="secondary-button" disabled={locked || !validCount || !withinBudget || !state.confirmed || !completed.some(trial => trial.trial_id === state.parentId)} onClick={() => onSubmit()}>{state.isRunning ? text("등록 중", "Registering") : text("반복 실험 등록", "Register replicates")}</button>
      {state.canRetry ? <button type="button" className="secondary-button" disabled={disabled} onClick={() => onSubmit(true)}>{text("동일 요청 확인/재시도", "Check / retry identical request")}</button> : null}
      <button type="button" className="secondary-button" disabled={disabled} onClick={onRefresh}>{text("실험 목록 새로고침", "Refresh trials")}</button>
    </div>
    {state.error ? <div className="error-box" role="alert"><p>{text("반복 등록을 확인하지 못했습니다. 자동 재전송하지 않습니다. 서버에서 이미 저장됐을 수 있으므로 동일 요청을 확인하거나 목록을 새로고침하세요.", "Replicate registration could not be confirmed. No automatic retry is sent. The server may already have saved it; check the identical request or refresh the trial list.")}</p><code>{state.error}</code></div> : null}
    {state.created ? <p className="notice-box" role="status">{text(`${state.created.trials.length}개 반복 trial 등록이 확인되었습니다. 목록 조회가 실패해도 저장된 실험은 유지됩니다.`, `${state.created.trials.length} replicate trials confirmed. A failed list refresh does not undo their registration.`)}</p> : null}
  </section>;
}
