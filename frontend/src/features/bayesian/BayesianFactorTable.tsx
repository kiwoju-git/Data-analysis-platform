import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";

type DraftState = ReturnType<typeof useBayesianStudyDraftState>;

export function BayesianFactorTable({ draft }: { draft: DraftState }) {
  return (
    <>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Factor ID</th>
              <th>표시 이름</th>
              <th>하한</th>
              <th>상한</th>
              <th>단위</th>
              <th>제거</th>
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
                  <input
                    aria-label={`${factor.name} 단위`}
                    value={factor.unit}
                    onChange={(event) =>
                      draft.updateFactor(factor.key, "unit", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={draft.factors.length === 1}
                    onClick={() => draft.removeFactor(factor.key)}
                  >
                    제거
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={draft.factors.length >= 6}
          onClick={draft.addFactor}
        >
          요인 추가
        </button>
      </div>
    </>
  );
}
