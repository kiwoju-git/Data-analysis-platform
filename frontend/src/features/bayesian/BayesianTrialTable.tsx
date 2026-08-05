import { useMemo, useState } from "react";

import type { BayesianStudyResponse } from "../../api";
import { coordinateText, type PendingTrialTransition } from "./bayesianDisplay";
import { BayesianTrialTransitionConfirmation } from "./BayesianTransitionConfirmations";

export function BayesianTrialTable({
  study,
  observations,
  pendingTransition,
  pendingObservationBatch,
  isSaving,
  actionsDisabled,
  onObservationChange,
  onObservationBatchApply,
  onRequestTransition,
  onRequestObservationBatch,
  onConfirmTransition,
  onConfirmObservationBatch,
  onCancelTransition,
  onCancelObservationBatch,
}: {
  study: BayesianStudyResponse;
  observations: Record<string, string>;
  pendingTransition: PendingTrialTransition | null;
  pendingObservationBatch: boolean;
  isSaving: boolean;
  actionsDisabled: boolean;
  onObservationChange: (trialId: string, value: string) => void;
  onObservationBatchApply: (values: Record<string, string>) => void;
  onRequestTransition: (trialId: string, action: "complete" | "abandon") => void;
  onRequestObservationBatch: () => void;
  onConfirmTransition: () => void;
  onConfirmObservationBatch: () => void;
  onCancelTransition: () => void;
  onCancelObservationBatch: () => void;
}) {
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteContent, setPasteContent] = useState("");
  const [pasteError, setPasteError] = useState<string | null>(null);
  const pendingTrials = useMemo(
    () => study.trials.filter((trial) => trial.state === "pending").sort((a, b) => a.trial_number - b.trial_number),
    [study.trials],
  );
  const entered = pendingTrials.filter((trial) => (observations[trial.trial_id] ?? "").trim() !== "");
  const invalid = entered.filter((trial) => !Number.isFinite(Number(observations[trial.trial_id])));

  function applyPaste(): void {
    const parsed = parseObservationPaste(pasteContent, pendingTrials);
    if (parsed.error !== null) {
      setPasteError(parsed.error);
      return;
    }
    onObservationBatchApply(parsed.values);
    setPasteContent("");
    setPasteError(null);
    setPasteOpen(false);
  }

  return (
    <section aria-labelledby="bayesian-trials-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-trials-title">Trial과 실제 관측</h4>
          <p>입력한 관측값은 한 번의 원자적 저장으로 완료 처리됩니다. 실험 포기는 개별 terminal transition입니다.</p>
        </div>
        <button className="secondary-button" disabled={pendingTrials.length === 0 || actionsDisabled || pendingObservationBatch} onClick={() => setPasteOpen((open) => !open)} type="button">관측값 붙여넣기</button>
      </div>
      {pasteOpen ? (
        <section className="notice-box bayesian-observation-paste" aria-labelledby="bayesian-observation-paste-title">
          <h5 id="bayesian-observation-paste-title">관측값 붙여넣기</h5>
          <textarea aria-label="Bayesian 관측값 붙여넣기" rows={6} value={pasteContent} onChange={(event) => { setPasteContent(event.currentTarget.value); setPasteError(null); }} placeholder={"94.1\n95.2\n93.8"} />
          <p>값 한 열은 trial 번호 순서대로, `trial`과 `response` 두 열은 지정한 trial에 적용합니다. 적용 후 일괄 저장 전 다시 확인할 수 있습니다.</p>
          {pasteError ? <div className="error-box" role="alert">{pasteError}</div> : null}
          <div className="button-row">
            <button className="secondary-button" onClick={() => setPasteOpen(false)} type="button">취소</button>
            <button className="primary-button" disabled={pasteContent.trim() === ""} onClick={applyPaste} type="button">앞 pending trial에 적용</button>
          </div>
        </section>
      ) : null}
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>Trial</th><th>종류</th><th>실제 조건</th><th>상태</th><th>관측값</th><th>처리</th></tr></thead>
          <tbody>
            {study.trials.map((trial) => (
              <tr key={trial.trial_id}>
                <td>{trial.trial_number}</td>
                <td>{trial.origin === "recommendation" ? "추천" : "초기 설계"}</td>
                <td>{coordinateText(trial.actual_coordinates)}</td>
                <td>{trialStateLabel(trial.state)}</td>
                <td>
                  {trial.state === "pending" ? (
                    <input
                      aria-invalid={(observations[trial.trial_id] ?? "").trim() !== "" && !Number.isFinite(Number(observations[trial.trial_id])) ? true : undefined}
                      aria-label={`Trial ${trial.trial_number} 관측값`}
                      inputMode="decimal"
                      value={observations[trial.trial_id] ?? ""}
                      disabled={study.status !== "active" || isSaving || pendingObservationBatch}
                      onChange={(event) => onObservationChange(trial.trial_id, event.currentTarget.value)}
                    />
                  ) : trial.objective_value}
                </td>
                <td>
                  <button type="button" className="secondary-button" disabled={trial.state !== "pending" || actionsDisabled || pendingObservationBatch} onClick={() => onRequestTransition(trial.trial_id, "abandon")}>실험 포기</button>
                  {pendingTransition?.trialId === trial.trial_id ? (
                    <BayesianTrialTransitionConfirmation
                      trial={trial}
                      action="abandon"
                      objectiveValue=""
                      isSaving={isSaving}
                      onConfirm={onConfirmTransition}
                      onCancel={onCancelTransition}
                    />
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="doe-action-bar">
        <div className="doe-validation-summary">입력 {entered.length.toLocaleString()}건 · 빈칸 {(pendingTrials.length - entered.length).toLocaleString()}건{invalid.length > 0 ? ` · 오류 ${invalid.length.toLocaleString()}건` : ""}</div>
        <button className="primary-button" disabled={actionsDisabled || entered.length === 0 || invalid.length > 0} onClick={onRequestObservationBatch} type="button">입력한 관측 {entered.length.toLocaleString()}건 저장</button>
      </div>
      {pendingObservationBatch ? (
        <div className="confirmation-box" role="alertdialog" aria-labelledby="bayesian-batch-confirm-title">
          <strong id="bayesian-batch-confirm-title">관측값 {entered.length.toLocaleString()}건 저장</strong>
          <p>입력한 관측값은 완료된 실제 실험값으로 기록되며 직접 수정할 수 없습니다. 계속하시겠습니까?</p>
          <div className="button-row"><button className="secondary-button" disabled={isSaving} onClick={onCancelObservationBatch} type="button">취소</button><button className="primary-button" disabled={isSaving} onClick={onConfirmObservationBatch} type="button">{isSaving ? "저장 중" : `${entered.length.toLocaleString()}건 저장`}</button></div>
        </div>
      ) : null}
    </section>
  );
}

function parseObservationPaste(
  content: string,
  pendingTrials: BayesianStudyResponse["trials"],
): { values: Record<string, string>; error: string | null } {
  const lines = content.replace(/\r\n?/g, "\n").split("\n").filter((line) => line.trim() !== "");
  if (lines.length === 0) return { values: {}, error: "붙여넣은 관측값이 없습니다." };
  const separator = lines[0].includes("\t") ? "\t" : lines[0].includes(",") ? "," : null;
  let rows = lines.map((line) => separator === null ? [line.trim()] : line.split(separator).map((cell) => cell.trim()));
  if (rows[0].some((cell) => /trial|response|반응|관측/i.test(cell))) rows = rows.slice(1);
  if (rows.length === 0) return { values: {}, error: "header 아래에 관측 데이터가 없습니다." };
  const values: Record<string, string> = {};
  if (rows.every((row) => row.length === 1)) {
    if (rows.length > pendingTrials.length) return { values: {}, error: "붙여넣은 값 수가 pending trial 수보다 많습니다." };
    rows.forEach((row, index) => { values[pendingTrials[index].trial_id] = row[0]; });
  } else if (rows.every((row) => row.length >= 2)) {
    const byNumber = new Map(pendingTrials.map((trial) => [String(trial.trial_number), trial]));
    for (const row of rows) {
      const trial = byNumber.get(row[0]);
      if (trial === undefined) return { values: {}, error: `pending Trial ${row[0]}을 찾을 수 없습니다.` };
      if (trial.trial_id in values) return { values: {}, error: `Trial ${row[0]}이 중복되었습니다.` };
      values[trial.trial_id] = row[1];
    }
  } else return { values: {}, error: "모든 행을 값 한 열 또는 trial/response 두 열로 맞추세요." };
  if (Object.values(values).some((value) => value === "" || !Number.isFinite(Number(value)))) return { values: {}, error: "유한한 숫자가 아닌 관측값이 있습니다." };
  return { values, error: null };
}

function trialStateLabel(state: BayesianStudyResponse["trials"][number]["state"]): string {
  if (state === "pending") return "대기";
  if (state === "completed") return "완료";
  return "실험 포기";
}
