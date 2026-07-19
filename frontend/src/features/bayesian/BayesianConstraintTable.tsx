import type { ConstraintDraft } from "../../bayesianStudyDraft";
import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";

type DraftState = ReturnType<typeof useBayesianStudyDraftState>;

export function BayesianConstraintTable({ draft }: { draft: DraftState }) {
  return (
    <>
      <div className="panel-heading">
        <div>
          <h4>실제 단위 선형 제약</h4>
          <p>각 제약은 입력한 factor 단위에서 계산되며 0이 아닌 계수가 필요합니다.</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          disabled={draft.constraints.length >= 16}
          onClick={draft.addConstraint}
        >
          제약 추가
        </button>
      </div>
      {draft.constraints.length === 0 ? (
        <p className="cell-subtext">선형 제약이 없으면 선언한 factor bounds만 적용됩니다.</p>
      ) : (
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>제약 ID</th>
                <th>이름</th>
                {draft.factors.map((factor) => (
                  <th key={factor.key}>{factor.factorId || `factor_${factor.key}`} 계수</th>
                ))}
                <th>관계</th>
                <th>우변</th>
                <th>제거</th>
              </tr>
            </thead>
            <tbody>
              {draft.constraints.map((constraint, index) => (
                <tr key={constraint.key}>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} ID`}
                      value={constraint.constraintId}
                      onChange={(event) =>
                        draft.updateConstraint(
                          constraint.key,
                          "constraintId",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} 이름`}
                      value={constraint.name}
                      onChange={(event) =>
                        draft.updateConstraint(
                          constraint.key,
                          "name",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  {draft.factors.map((factor) => (
                    <td key={factor.key}>
                      <input
                        aria-label={`제약 ${index + 1} ${factor.factorId || `factor_${factor.key}`} 계수`}
                        inputMode="decimal"
                        value={constraint.coefficients[factor.key] ?? ""}
                        placeholder="0"
                        onChange={(event) =>
                          draft.updateConstraintCoefficient(
                            constraint.key,
                            factor.key,
                            event.currentTarget.value,
                          )
                        }
                      />
                    </td>
                  ))}
                  <td>
                    <select
                      aria-label={`제약 ${index + 1} 관계`}
                      value={constraint.relation}
                      onChange={(event) =>
                        draft.updateConstraint(
                          constraint.key,
                          "relation",
                          event.currentTarget.value as ConstraintDraft["relation"],
                        )
                      }
                    >
                      <option value="less_than_or_equal">≤</option>
                      <option value="greater_than_or_equal">≥</option>
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} 우변`}
                      inputMode="decimal"
                      value={constraint.bound}
                      onChange={(event) =>
                        draft.updateConstraint(
                          constraint.key,
                          "bound",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="secondary-button"
                      aria-label={`제약 ${index + 1} 제거`}
                      onClick={() => draft.removeConstraint(constraint.key)}
                    >
                      제거
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
