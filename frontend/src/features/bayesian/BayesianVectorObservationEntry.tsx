import { useEffect, useRef } from "react";
import type { BayesianStudyResponse } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { formatExactNumericValue } from "../../statisticalNumberFormat";
import { boText } from "./boNoisePolicy";
import { useBayesianVectorEntry } from "./hooks/useBayesianVectorEntry";
import { vectorDraftCell } from "./bayesianVectorDraft";
import "./bayesianVectorEntry.css";

export function BayesianVectorObservationEntry({ study, onCommitted, onRefresh, disabled }: {
  study: BayesianStudyResponse;
  onCommitted: (study: BayesianStudyResponse, source: string) => void;
  onRefresh: () => void;
  disabled: boolean;
}) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const entry = useBayesianVectorEntry(study, onCommitted);
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (entry.error) errorRef.current?.focus(); }, [entry.error]);
  if (study.objective.goal_type !== "desirability") return null;
  const responses = study.objective.responses;
  const pending = study.trials.filter(t => t.state === "pending");
  const closedDrafts = study.trials.filter(t => t.state !== "pending" && responses.some(r => vectorDraftCell(entry.draft, t.trial_id, r.response_id).trim() !== ""));
  return <section aria-label={text("다중 반응 관측 입력", "Multiresponse observation entry")}>
    <h4>{text("실제 실험 관측값 입력", "Enter measured experiment responses")}</h4>
    <p>{text("입력한 실험은 모든 반응값이 필요합니다. 완전히 빈 행은 저장하지 않습니다. 저장 후 기존 값을 덮어쓰지 않습니다.",
      "Every entered trial requires all responses. Entirely blank rows are not saved. Saved measurements cannot be overwritten.")}</p>
    {entry.error ? <div className="error-box" role="alert" tabIndex={-1} ref={errorRef}>
      <p>{entry.error === "bayesian_vector_observations_invalid"
        ? text("입력한 각 행의 모든 반응에 유효한 숫자를 입력하세요. 빈 값은 0이 아닙니다.", "Enter valid numbers for every response in each entered row. A blank value is not zero.")
        : text("저장 상태를 확인하지 못했습니다. 입력은 유지됩니다. 이력 충돌이면 최신 이력을 확인한 뒤 다시 검토하세요.", "The saved state could not be confirmed. Inputs are retained. For a history conflict, refresh the history and review again.")}</p>
      <small>{text("오류 코드", "Error code")}: {entry.error}</small>
    </div> : null}
    {entry.mayHaveCommitted ? <div className="notice-box" role="status">{text("서버에 이미 저장되었을 수 있습니다. 같은 요청 재시도 또는 최신 이력 조회로 확인하세요. 새 요청이 기존 측정값을 덮어쓰지는 않습니다.",
      "The server may already have saved the measurements. Retry the same request or refresh the history to verify. A new request will not overwrite existing measurements.")}</div> : null}
    {closedDrafts.length ? <section className="warning-box" aria-label={text("저장 이력과 내 입력 비교", "Compare saved history with my inputs")}>
      <h5>{text("다른 요청으로 종료된 실험의 미저장 입력", "Unsaved inputs for trials closed by another request")}</h5>
      <p>{text("원래 입력을 보존했습니다. 저장값을 확인한 뒤 미저장 입력만 명시적으로 폐기할 수 있습니다.", "Your original inputs are retained. Compare the saved values, then explicitly discard only these unsaved inputs.")}</p>
      <div className="table-wrap"><table className="result-table"><thead><tr><th scope="col">Trial</th>
        <th scope="col">{text("반응", "Response")}</th><th scope="col">{text("내 입력", "My input")}</th><th scope="col">{text("저장값", "Saved value")}</th></tr></thead>
        <tbody>{closedDrafts.flatMap(trial => responses.map(r => <tr key={`${trial.trial_id}:${r.response_id}`}><th scope="row">{trial.trial_number}</th>
          <td>{r.name} {r.unit ?? ""}</td><td>{vectorDraftCell(entry.draft, trial.trial_id, r.response_id) || "-"}</td><td>{formatExactNumericValue(trial.response_values?.[r.response_id])}</td></tr>))}</tbody>
      </table></div>
      <button type="button" className="secondary-button" disabled={disabled || entry.isSaving} onClick={entry.discardClosedDrafts}>
        {text("종료 실험의 미저장 입력 폐기", "Discard unsaved inputs for closed trials")}</button>
    </section> : null}
    {study.status === "active" && pending.length ? <>
      <div className="table-wrap"><table className="result-table bo-vector-entry">
        <caption>{text("대기 실험 · 원래 반응 단위", "Pending experiments · original response units")}</caption>
        <thead><tr><th scope="col">Trial</th>{study.factors.map(f => <th scope="col" key={f.factor_id}>{f.name} {f.unit ? `[${f.unit}]` : ""}</th>)}
          {responses.map(r => <th scope="col" key={r.response_id}>{r.name} {r.unit ? `[${r.unit}]` : ""}</th>)}</tr></thead>
        <tbody>{pending.map(trial => <tr key={trial.trial_id}><th scope="row">{trial.trial_number}</th>
          {study.factors.map(f => <td key={f.factor_id}>{formatExactNumericValue(trial.actual_coordinates[f.factor_id])}</td>)}
          {responses.map(r => <td key={r.response_id}><input inputMode="decimal" disabled={disabled}
            data-trial-id={trial.trial_id} data-response-id={r.response_id}
            aria-label={`Trial ${trial.trial_number} ${r.name}${r.unit ? ` [${r.unit}]` : ""}`}
            value={vectorDraftCell(entry.draft, trial.trial_id, r.response_id)}
            onChange={event => entry.edit(trial.trial_id, r.response_id, event.currentTarget.value)} /></td>)}
        </tr>)}</tbody>
      </table></div>
      {!entry.review ? <button type="button" className="primary-button" disabled={disabled || entry.isSaving || closedDrafts.length > 0} onClick={entry.preview}>
        {text("저장할 관측값 검토", "Review measurements")}</button> : <section className="notice-box" aria-label={text("관측 저장 확인", "Confirm measured responses")}>
        <h5>{text("다음 실제 측정값을 저장합니다", "Save these measured responses")}</h5>
        <div className="table-wrap"><table className="result-table"><thead><tr><th scope="col">Trial</th>{responses.map(r => <th scope="col" key={r.response_id}>{r.name} {r.unit ?? ""}</th>)}</tr></thead>
          <tbody>{entry.review.request.observations.map(observation => <tr key={observation.trial_id}>
            <th scope="row">{pending.find(t => t.trial_id === observation.trial_id)?.trial_number}</th>
            {responses.map(r => <td key={r.response_id}>{formatExactNumericValue("response_values" in observation ? observation.response_values[r.response_id] : null)}</td>)}
          </tr>)}</tbody></table></div>
        <div className="bo-vector-actions"><button type="button" className="primary-button" disabled={disabled || entry.isSaving} onClick={() => void entry.confirm()}>
          {entry.isSaving ? text("저장 중", "Saving") : entry.failed ? text("같은 요청 다시 저장", "Retry same request") : text("관측값 저장 확정", "Confirm measurements")}</button>
          <button type="button" className="secondary-button" onClick={entry.cancel}>{text("검토 취소", "Cancel review")}</button></div>
      </section>}
    </> : <p>{text("입력 가능한 대기 실험이 없습니다.", "No pending experiments are available for entry.")}</p>}
    <div className="bo-vector-actions"><button type="button" className="secondary-button" disabled={disabled || entry.isSaving} onClick={onRefresh}>{text("최신 이력 확인", "Refresh history")}</button></div>
  </section>;
}
