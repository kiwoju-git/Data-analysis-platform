import type { useBayesianStudyCatalogState } from "./hooks/useBayesianStudyCatalogState";

type CatalogState = ReturnType<typeof useBayesianStudyCatalogState>;

export function BayesianStudyCatalog({
  state,
  disabled,
  onSelect,
  onCreateNew,
}: {
  state: CatalogState;
  disabled: boolean;
  onSelect: (studyId: string | null) => void;
  onCreateNew: () => void;
}) {
  const selectedIsOutsidePage =
    state.selectedStudyId !== null && state.selectedSummary === null;
  return (
    <section aria-labelledby="bayesian-study-catalog-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-study-catalog-title">Study 선택</h4>
          <p>저장된 metadata catalog를 페이지 단위로 탐색하거나 새 Study를 만듭니다.</p>
        </div>
        <button type="button" className="primary-button" disabled={disabled} onClick={onCreateNew}>
          새 Study 만들기
        </button>
      </div>
      <label>
        <span>저장된 study</span>
        <select
          aria-label="저장된 Bayesian study"
          value={state.selectedStudyId ?? ""}
          disabled={disabled || state.isLoading}
          onChange={(event) => onSelect(event.currentTarget.value || null)}
        >
          <option value="">선택</option>
          {selectedIsOutsidePage ? (
            <option value={state.selectedStudyId!}>
              ID로 복원한 Study · {shortId(state.selectedStudyId!)}
            </option>
          ) : null}
          {state.catalog?.items.map((item) => (
            <option key={item.study_id} value={item.study_id}>
              {item.name} · {item.status} · 완료 {item.completed_trial_count}
            </option>
          ))}
        </select>
      </label>
      {state.isLoading ? <p className="cell-subtext" role="status">Study catalog 확인 중</p> : null}
      {state.error !== null ? (
        <div className="error-box" role="alert">
          <p>Study catalog를 확인하지 못했습니다. 오류 코드: {state.error}</p>
          <button type="button" className="secondary-button" onClick={state.onRefresh}>다시 시도</button>
        </div>
      ) : null}
      {state.catalog !== null && state.catalog.total > state.catalog.limit ? (
        <div className="result-pagination" aria-label="Bayesian study catalog 페이지 이동">
          <button
            type="button"
            disabled={state.isLoading || state.catalog.offset === 0}
            onClick={() => state.onPageChange(Math.max(0, state.catalog!.offset - state.catalog!.limit))}
          >
            이전
          </button>
          <span>
            {state.catalog.items.length === 0 ? 0 : state.catalog.offset + 1}-
            {state.catalog.offset + state.catalog.items.length} / {state.catalog.total}
          </span>
          <button
            type="button"
            disabled={
              state.isLoading ||
              state.catalog.offset + state.catalog.items.length >= state.catalog.total
            }
            onClick={() => state.onPageChange(state.catalog!.offset + state.catalog!.limit)}
          >
            다음
          </button>
        </div>
      ) : null}
    </section>
  );
}

function shortId(value: string) {
  return value.length <= 16 ? value : `${value.slice(0, 8)}…${value.slice(-6)}`;
}
