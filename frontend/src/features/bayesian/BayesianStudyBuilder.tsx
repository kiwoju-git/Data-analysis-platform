import { BayesianConstraintTable } from "./BayesianConstraintTable";
import { BayesianFactorTable } from "./BayesianFactorTable";
import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";

type DraftState = ReturnType<typeof useBayesianStudyDraftState>;

export function BayesianStudyBuilder({
  draft,
  isCreating,
  disabled,
  onCreate,
  onCancel,
}: {
  draft: DraftState;
  isCreating: boolean;
  disabled: boolean;
  onCreate: () => void;
  onCancel: () => void;
}) {
  return (
    <section aria-labelledby="bayesian-study-builder-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-study-builder-title">
            {draft.predecessorStudyId === null ? "새 Study 정의" : "Successor Study 정의"}
          </h4>
          <p>Factor bounds, objective, 초기 설계와 실제 단위 제약을 고정합니다.</p>
        </div>
      </div>
      <div className="option-grid">
        <label>
          <span>Study 이름</span>
          <input value={draft.studyName} onChange={(event) => draft.setStudyName(event.currentTarget.value)} />
        </label>
        <label>
          <span>목적 반응</span>
          <input value={draft.objectiveName} onChange={(event) => draft.setObjectiveName(event.currentTarget.value)} />
        </label>
        <label>
          <span>반응 단위</span>
          <input value={draft.objectiveUnit} onChange={(event) => draft.setObjectiveUnit(event.currentTarget.value)} />
        </label>
        <label>
          <span>방향</span>
          <select
            value={draft.direction}
            onChange={(event) =>
              draft.setDirection(event.currentTarget.value as "minimize" | "maximize")
            }
          >
            <option value="maximize">최대화</option>
            <option value="minimize">최소화</option>
          </select>
        </label>
        <label>
          <span>초기 trial 수</span>
          <input
            inputMode="numeric"
            value={draft.initialDesignSize}
            onChange={(event) => draft.setInitialDesignSize(event.currentTarget.value)}
          />
          <span className="cell-subtext">
            현재 요인 {draft.factors.length}개에는 최소 {draft.minimumInitialDesignSize}개가 필요합니다.
          </span>
        </label>
        <label>
          <span>초기 설계 seed</span>
          <input
            inputMode="numeric"
            value={draft.initialDesignSeed}
            onChange={(event) => draft.setInitialDesignSeed(event.currentTarget.value)}
          />
        </label>
      </div>
      {draft.predecessorStudyId !== null ? (
        <BayesianSuccessorSeedNotice
          sameSeed={draft.sameSeedAsPredecessor}
          onGenerateSeed={draft.generateNewSeed}
        />
      ) : null}
      <BayesianFactorTable draft={draft} />
      <BayesianConstraintTable draft={draft} />
      <div className="button-row">
        <button type="button" className="primary-button" disabled={disabled} onClick={onCreate}>
          {isCreating
            ? "생성 중"
            : draft.predecessorStudyId === null
              ? "Study 생성"
              : "Successor study 생성"}
        </button>
        <button type="button" className="secondary-button" disabled={isCreating} onClick={onCancel}>
          {draft.predecessorStudyId === null ? "새 Study 만들기 닫기" : "Successor 생성 취소"}
        </button>
      </div>
    </section>
  );
}

export function BayesianSuccessorSeedNotice({
  sameSeed,
  onGenerateSeed,
}: {
  sameSeed: boolean;
  onGenerateSeed: () => void;
}) {
  return (
    <div className="notice-box" role="status">
      <p>
        Factor, objective, constraint, seed만 새 정의 초안으로 복사합니다. 기존 관측,
        history, recommendation은 복사하지 않습니다.
      </p>
      {sameSeed ? (
        <p>동일한 seed를 사용하면 동일한 초기 조건이 다시 생성될 수 있습니다.</p>
      ) : (
        <p>새 successor에 변경된 seed를 사용합니다.</p>
      )}
      <button type="button" className="secondary-button" onClick={onGenerateSeed}>
        새 random seed 생성
      </button>
    </div>
  );
}
