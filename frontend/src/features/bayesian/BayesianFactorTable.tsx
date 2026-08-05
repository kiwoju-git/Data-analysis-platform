import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";
import { DoeFactorEditor } from "../../doe/DoeFormPrimitives";

type DraftState = ReturnType<typeof useBayesianStudyDraftState>;

export function BayesianFactorTable({ draft }: { draft: DraftState }) {
  return (
    <DoeFactorEditor
      title="요인 범위"
      description="최적화할 연속형 요인의 식별자, 표시 이름과 실제 단위 범위를 입력합니다."
      action={
        <button
          type="button"
          className="secondary-button"
          disabled={draft.factors.length >= 6}
          onClick={draft.addFactor}
        >
          요인 추가
        </button>
      }
    >
      <div className="table-wrap">
        <table className="result-table doe-factor-table bayesian-factor-table">
          <colgroup>
            <col className="bayesian-factor-id-column" />
            <col className="bayesian-factor-name-column" />
            <col className="bayesian-factor-bound-column" />
            <col className="bayesian-factor-bound-column" />
            <col className="doe-factor-domain-column" />
            <col className="bayesian-factor-bound-column" />
            <col className="bayesian-factor-bound-column" />
            <col className="bayesian-factor-unit-column" />
            <col className="bayesian-factor-action-column" />
          </colgroup>
          <thead>
            <tr>
              <th>요인 ID</th>
              <th>표시 이름</th>
              <th>하한</th>
              <th>상한</th>
              <th>설정 방식</th>
              <th>실행 간격</th>
              <th>표시 자리수</th>
              <th>단위</th>
              <th className="bayesian-factor-action-cell">작업</th>
            </tr>
          </thead>
          <tbody>
            {draft.factors.map((factor, index) => (
              <tr key={factor.key}>
                <td>
                  <input
                    aria-label={`요인 ${index + 1} ID`}
                    value={factor.factorId}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "factorId", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`요인 ${index + 1} 이름`}
                    value={factor.name}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "name", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 하한`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "low", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 상한`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "high", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <select
                    aria-label={`${factor.name} 설정 방식`}
                    value={factor.domainKind ?? "continuous"}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "domainKind", event.currentTarget.value)
                    }
                  >
                    <option value="continuous">연속형</option>
                    <option value="discrete_numeric">일정 간격 숫자</option>
                  </select>
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 실행 간격`}
                    disabled={(factor.domainKind ?? "continuous") === "continuous"}
                    inputMode="decimal"
                    placeholder="-"
                    value={factor.step ?? ""}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "step", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 표시 자리수`}
                    inputMode="numeric"
                    placeholder="자동"
                    value={factor.displayDecimals ?? ""}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "displayDecimals", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 단위`}
                    value={factor.unit}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "unit", event.currentTarget.value)
                    }
                  />
                </td>
                <td className="bayesian-factor-action-cell">
                  <button
                    type="button"
                    className="secondary-button compact-button"
                    aria-label={`${factor.name} 요인 삭제`}
                    disabled={draft.factors.length === 1}
                    onClick={() => draft.removeFactor(factor.key)}
                  >
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DoeFactorEditor>
  );
}
