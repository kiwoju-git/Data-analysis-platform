import type {
  BayesianExecutionMode,
  BayesianExplorationProfile,
  BayesianRecommendationBatchItemResponse,
  BayesianRecommendationBatchResponse,
  BayesianRecommendationResponse,
  BayesianStudyResponse,
} from "../../api";
import {
  bayesianRecommendationBudgetBlocker,
  bayesianRecommendationStatus,
} from "../../bayesianStudyDraft";
import {
  batchReasonText,
  coordinateText,
  formatNumber,
} from "./bayesianDisplay";
import { DoeSettingsTable } from "../../doe/DoeSettingsTable";

const EXPLORATION_OPTIONS: Array<{
  value: BayesianExplorationProfile;
  label: string;
  description: string;
}> = [
  {
    value: "exploitation",
    label: "활용 우선",
    description: "현재 성과가 좋은 영역 근처를 더 중시합니다.",
  },
  {
    value: "balanced",
    label: "균형",
    description: "예측 성과와 불확실성을 함께 고려합니다.",
  },
  {
    value: "exploration",
    label: "탐색 우선",
    description: "아직 관측이 적고 불확실한 영역을 더 검토합니다.",
  },
  {
    value: "custom",
    label: "직접 설정",
    description: "표준화된 추가 개선 요구량 ξ를 직접 입력합니다.",
  },
];

export function BayesianRecommendationPanel({
  study,
  batch,
  recommendation,
  executionMode,
  batchSize,
  explorationProfile,
  customXi,
  totalTrialBudget,
  isRecommending,
  actionsDisabled,
  onExecutionModeChange,
  onBatchSizeChange,
  onExplorationProfileChange,
  onCustomXiChange,
  onBudgetChange,
  onRecommend,
}: {
  study: BayesianStudyResponse;
  batch: BayesianRecommendationBatchResponse | null;
  recommendation: BayesianRecommendationResponse | null;
  executionMode: BayesianExecutionMode;
  batchSize: string;
  explorationProfile: BayesianExplorationProfile;
  customXi: string;
  totalTrialBudget: string;
  isRecommending: boolean;
  actionsDisabled: boolean;
  onExecutionModeChange: (value: BayesianExecutionMode) => void;
  onBatchSizeChange: (value: string) => void;
  onExplorationProfileChange: (value: BayesianExplorationProfile) => void;
  onCustomXiChange: (value: string) => void;
  onBudgetChange: (value: string) => void;
  onRecommend: () => void;
}) {
  const parsedBatchSize =
    executionMode === "sequential_single" ? 1 : Number(batchSize);
  const parsedBudget = Number(totalTrialBudget);
  const budgetBlocker = bayesianRecommendationBudgetBlocker(
    study.trial_count,
    parsedBudget,
    study.recommendation_hard_trial_limit,
    Number.isInteger(parsedBatchSize) ? parsedBatchSize : 1,
  );
  const batchSizeInvalid =
    executionMode === "parallel_batch" &&
    (!Number.isInteger(parsedBatchSize) ||
      parsedBatchSize < 2 ||
      parsedBatchSize > 8);
  const customXiInvalid =
    explorationProfile === "custom" &&
    (!Number.isFinite(Number(customXi)) ||
      Number(customXi) < 0 ||
      Number(customXi) > 10);
  const disabled =
    actionsDisabled ||
    study.status !== "active" ||
    !study.recommendation_available ||
    budgetBlocker !== null ||
    batchSizeInvalid ||
    customXiInvalid ||
    isRecommending;
  const settingsDisabled =
    actionsDisabled || study.status !== "active" || isRecommending;
  const targetGoal = study.objective.goal_type === "match_target";

  return (
    <section aria-labelledby="bayesian-recommendation-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-recommendation-title">다음 실험 추천</h4>
          <p>
            최적화 목표는 실제 실험 반응이고, acquisition은 다음 확인 조건을
            고르는 계산 기준입니다.
          </p>
        </div>
      </div>

      <div className="bayesian-recommendation-settings">
        <DoeSettingsTable
          ariaLabel="Bayesian 다음 실험 추천 설정"
          fields={[
            {
              key: "execution-mode",
              label: "실행 방식",
              control: (
                <fieldset
                  className="segmented-fieldset doe-table-segmented"
                  disabled={settingsDisabled}
                >
                  <legend className="visually-hidden">실행 방식</legend>
                  <div className="segmented-control">
                    <label>
                      <input
                        type="radio"
                        name="bayesian-execution-mode"
                        value="sequential_single"
                        checked={executionMode === "sequential_single"}
                        onChange={() => onExecutionModeChange("sequential_single")}
                      />
                      <span>결과를 하나씩 반영</span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="bayesian-execution-mode"
                        value="parallel_batch"
                        checked={executionMode === "parallel_batch"}
                        onChange={() => onExecutionModeChange("parallel_batch")}
                      />
                      <span>여러 실험을 동시에 수행</span>
                    </label>
                  </div>
                </fieldset>
              ),
              helper:
                executionMode === "sequential_single"
                  ? "실제 결과를 입력한 뒤 GP를 갱신하여 다음 조건을 추천합니다."
                  : "같은 관측 이력을 기준으로 생성하며, batch 전체가 종료될 때까지 다음 추천을 차단합니다.",
            },
            {
              key: "batch-size",
              label: "한 번에 추천할 실험 수",
              controlId: "bayesian-recommendation-batch-size",
              control: (
                <input
                  id="bayesian-recommendation-batch-size"
                  aria-describedby="bayesian-recommendation-batch-size-help"
                  inputMode="numeric"
                  value={batchSize}
                  disabled={
                    settingsDisabled || executionMode === "sequential_single"
                  }
                  onChange={(event) =>
                    onBatchSizeChange(event.currentTarget.value)
                  }
                />
              ),
              helper:
                executionMode === "sequential_single"
                  ? "순차 방식은 1개로 고정됩니다."
                  : "동시에 수행 가능한 수를 2~8개에서 선택하세요.",
              helperId: "bayesian-recommendation-batch-size-help",
            },
            {
              key: "budget",
              label: "전체 trial 예산",
              controlId: "bayesian-recommendation-budget",
              control: (
                <input
                  id="bayesian-recommendation-budget"
                  aria-describedby="bayesian-recommendation-budget-help"
                  inputMode="numeric"
                  value={totalTrialBudget}
                  disabled={settingsDisabled}
                  onChange={(event) => onBudgetChange(event.currentTarget.value)}
                />
              ),
              helper: `현재 ${study.trial_count}개 · hard limit ${study.recommendation_hard_trial_limit}개`,
              helperId: "bayesian-recommendation-budget-help",
            },
          ]}
        />

        <DoeSettingsTable
          ariaLabel="Bayesian 획득함수 설정"
          fields={[
            {
              key: "goal",
              label: "최적화 목표",
              control: <strong>{objectiveSummary(study)}</strong>,
            },
            {
              key: "acquisition",
              label: "획득함수",
              control: (
                <strong>
                  {targetGoal
                    ? "Expected Target Improvement"
                    : "Expected Improvement (EI)"}
                </strong>
              ),
            },
          ]}
        />

        <DoeSettingsTable
          ariaLabel="Bayesian 탐색 활용 설정"
          fields={[
            {
              key: "exploration",
              label: "탐색·활용 성향",
              control: (
                <fieldset
                  className="bayesian-exploration-fieldset doe-table-segmented"
                  disabled={settingsDisabled}
                >
                  <legend className="visually-hidden">탐색·활용 성향</legend>
                  <div className="bayesian-exploration-grid">
                    {EXPLORATION_OPTIONS.map((option) => (
                      <label
                        key={option.value}
                        className={
                          explorationProfile === option.value ? "is-selected" : ""
                        }
                      >
                        <span>
                          <input
                            type="radio"
                            name="bayesian-exploration-profile"
                            value={option.value}
                            checked={explorationProfile === option.value}
                            onChange={() =>
                              onExplorationProfileChange(option.value)
                            }
                          />
                          <strong>{option.label}</strong>
                        </span>
                        <small>{option.description}</small>
                      </label>
                    ))}
                  </div>
                </fieldset>
              ),
            },
            ...(explorationProfile === "custom"
              ? [
                  {
                    key: "xi",
                    label: "표준화 ξ (0~10)",
                    controlId: "bayesian-custom-xi",
                    control: (
                      <input
                        id="bayesian-custom-xi"
                        inputMode="decimal"
                        value={customXi}
                        onChange={(event) =>
                          onCustomXiChange(event.currentTarget.value)
                        }
                      />
                    ),
                  },
                ]
              : []),
          ]}
        />

        <details>
          <summary>EI와 고급 탐색 설정</summary>
          <div className="info-box">
            <p>
              μ는 GP 예측 평균, σ는 posterior 불확실성, incumbent는 현재
              최선의 실제 관측, ξ는 추가 개선 요구량입니다. 알고리즘은 실행
              가능한 새 후보 중 acquisition 값이 큰 조건을 찾습니다.
            </p>
            <p>
              내부 후보 풀은 단계당 256개이며 추천 개수와 다른 값입니다.
              batch는 exact joint qEI가 아니라 앞선 조건을 posterior-mean
              fantasy로 조건화하는 deterministic greedy 정책입니다.
            </p>
          </div>
        </details>
      </div>

      {batchSizeInvalid ? (
        <p className="warning-box" role="status">
          병렬 batch는 2~8개를 선택하세요.
        </p>
      ) : budgetBlocker !== null ? (
        <p className="warning-box" role="status">
          남은 trial 예산보다 batch 수가 큽니다. 예산 또는 추천 수를
          조정하세요.
        </p>
      ) : !study.recommendation_available ? (
        <p className="cell-subtext">
          추천 차단 사유: {study.recommendation_blockers.join(", ")}. 최소
          완료 관측은 {study.recommendation_minimum_completed_observations}
          개입니다.
        </p>
      ) : null}

      <div className="button-row">
        <button
          type="button"
          className="primary-button"
          disabled={disabled}
          onClick={onRecommend}
        >
          {isRecommending ? "추천 batch 계산 중" : "추천 batch 생성"}
        </button>
      </div>

      {batch !== null ? (
        <BayesianBatchResult batch={batch} />
      ) : recommendation !== null ? (
        <LegacyRecommendationResult recommendation={recommendation} />
      ) : null}
    </section>
  );
}

function BayesianBatchResult({
  batch,
}: {
  batch: BayesianRecommendationBatchResponse;
}) {
  return (
    <section aria-labelledby="bayesian-batch-result-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-batch-result-title">추천 batch 결과</h4>
          <p>
            {batch.batch_size}개 조건은 동일한 관측 이력을 기준으로
            생성되었습니다.
          </p>
        </div>
        <span className="status-pill">{batchStateLabel(batch.batch_state)}</span>
      </div>
      <div className="table-wrap">
        <table className="result-table bayesian-batch-result-table">
          <thead>
            <tr>
              <th>순위</th>
              <th>추천 조건</th>
              <th>예측 평균</th>
              <th>불확실성</th>
              <th>
                {batch.acquisition.kind === "expected_target_improvement"
                  ? "Target EI"
                  : "EI"}
              </th>
              <th>추천 이유</th>
              <th>현재 상태</th>
            </tr>
          </thead>
          <tbody>
            {batch.items.map((item) => (
              <BatchItemRow key={item.item_id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="cell-subtext">
        fantasy 값은 같은 batch의 후보 다양화를 위한 임시 조건화 값이며 실제
        관측이나 trial 결과로 저장되지 않습니다. 추천은 전역 최적을 보장하지
        않습니다. 실제 확인 실험이 필요합니다.
      </p>
    </section>
  );
}

function BatchItemRow({
  item,
}: {
  item: BayesianRecommendationBatchItemResponse;
}) {
  return (
    <tr>
      <td>{item.rank}</td>
      <td>{coordinateText(item.actual_coordinates)}</td>
      <td>{formatNumber(item.predicted_objective_mean)}</td>
      <td>{formatNumber(item.posterior_standard_deviation)}</td>
      <td>{formatNumber(item.acquisition_value)}</td>
      <td>
        <strong>{batchReasonText(item)}</strong>
        <details>
          <summary>왜 이 조건?</summary>
          <dl className="bayesian-reason-metrics">
            <div>
              <dt>현재 최선값</dt>
              <dd>{formatNumber(item.incumbent_objective)}</dd>
            </div>
            <div>
              <dt>평균 개선 항</dt>
              <dd>
                {formatNumber(
                  item.acquisition_breakdown.mean_improvement_term,
                )}
              </dd>
            </div>
            <div>
              <dt>불확실성 항</dt>
              <dd>
                {formatNumber(
                  item.acquisition_breakdown.uncertainty_term,
                )}
              </dd>
            </div>
            <div>
              <dt>표준화 ξ</dt>
              <dd>
                {formatNumber(
                  item.acquisition_breakdown.xi_standardized,
                )}
              </dd>
            </div>
            <div>
              <dt>가장 가까운 기존 trial 거리</dt>
              <dd>
                {item.nearest_existing_trial_distance === null
                  ? "-"
                  : formatNumber(item.nearest_existing_trial_distance)}
              </dd>
            </div>
            <div>
              <dt>앞선 batch 후보 거리</dt>
              <dd>
                {item.nearest_earlier_batch_item_distance === null
                  ? "-"
                  : formatNumber(
                      item.nearest_earlier_batch_item_distance,
                    )}
              </dd>
            </div>
            <div>
              <dt>Fantasy step</dt>
              <dd>{item.fantasy_step}</dd>
            </div>
          </dl>
          {item.constraint_evaluations.length > 0 ? (
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>제약</th>
                    <th>좌변</th>
                    <th>관계</th>
                    <th>한계</th>
                    <th>Slack</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {item.constraint_evaluations.map((evaluation) => (
                    <tr key={evaluation.constraint_id}>
                      <td>{evaluation.constraint_id}</td>
                      <td>{formatNumber(evaluation.lhs)}</td>
                      <td>
                        {evaluation.relation === "less_than_or_equal"
                          ? "≤"
                          : "≥"}
                      </td>
                      <td>{formatNumber(evaluation.bound)}</td>
                      <td>{formatNumber(evaluation.slack)}</td>
                      <td>{evaluation.satisfied ? "충족" : "위반"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </details>
      </td>
      <td>{item.current_trial.state}</td>
    </tr>
  );
}

function LegacyRecommendationResult({
  recommendation,
}: {
  recommendation: BayesianRecommendationResponse;
}) {
  const status = bayesianRecommendationStatus(recommendation);
  return (
    <section aria-labelledby="bayesian-legacy-recommendation-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-legacy-recommendation-title">
            기존 단일 추천
          </h4>
          <p>이전 schema의 batch size 1 추천을 읽기 전용으로 복원했습니다.</p>
        </div>
        <span className={`status-pill ${status.className}`}>
          {status.label}
        </span>
      </div>
      <div className="metadata-grid">
        <span>추천 조건</span>
        <strong>
          {coordinateText(
            recommendation.result.recommended_actual_coordinates,
          )}
        </strong>
        <span>예측 평균</span>
        <strong>
          {formatNumber(recommendation.result.predicted_objective_mean)}
        </strong>
        <span>Posterior 표준편차</span>
        <strong>
          {formatNumber(
            recommendation.result.posterior_standard_deviation,
          )}
        </strong>
        <span>Expected Improvement</span>
        <strong>
          {formatNumber(recommendation.result.expected_improvement)}
        </strong>
      </div>
    </section>
  );
}

function objectiveSummary(study: BayesianStudyResponse) {
  if (study.objective.goal_type === "match_target") {
    const tolerance =
      study.objective.target_tolerance === null
        ? ""
        : ` ± ${formatNumber(study.objective.target_tolerance)}`;
    return `${study.objective.name} 목표 ${formatNumber(
      study.objective.target_value ?? Number.NaN,
    )}${tolerance}`;
  }
  return `${study.objective.name} ${
    study.objective.goal_type === "maximize" ? "최대화" : "최소화"
  }`;
}

function batchStateLabel(
  state: BayesianRecommendationBatchResponse["batch_state"],
) {
  if (state === "pending") return "실험 대기";
  if (state === "partially_completed") return "일부 종료";
  if (state === "completed") return "전체 완료";
  if (state === "abandoned") return "전체 포기";
  return "완료·포기 혼합";
}
