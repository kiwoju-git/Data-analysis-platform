import { useCallback, useMemo, useState } from "react";

import { getAnalysisRunErrorDetails } from "../../analysisRunErrors";
import { BayesianRecommendationPanel } from "./BayesianRecommendationPanel";
import { BayesianStudyBuilder } from "./BayesianStudyBuilder";
import { BayesianStudyCatalog } from "./BayesianStudyCatalog";
import { BayesianStudyClosePanel } from "./BayesianStudyClosePanel";
import { BayesianStudyDeletionPanel } from "./BayesianStudyDeletionPanel";
import { BayesianStudySummary } from "./BayesianStudySummary";
import { BayesianTrialTable } from "./BayesianTrialTable";
import { validBayesianId } from "./bayesianDisplay";
import { useBayesianRecommendationState } from "./hooks/useBayesianRecommendationState";
import { useBayesianRetentionState } from "./hooks/useBayesianRetentionState";
import { useBayesianStudyCatalogState } from "./hooks/useBayesianStudyCatalogState";
import { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";
import { useBayesianStudyLifecycleState } from "./hooks/useBayesianStudyLifecycleState";

export function BayesianOptimizationWorkspace() {
  const initialQuery = useMemo(
    () => new URLSearchParams(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialStudyId = validBayesianId(initialQuery.get("study_id"));
  const initialRecommendationId = validBayesianId(initialQuery.get("recommendation_id"));
  const [requestedRecommendationId, setRequestedRecommendationId] =
    useState(initialRecommendationId);
  const [builderOpen, setBuilderOpen] = useState(initialStudyId === null);
  const catalog = useBayesianStudyCatalogState(initialStudyId);
  const draft = useBayesianStudyDraftState();
  const lifecycle = useBayesianStudyLifecycleState(catalog.selectedStudyId);
  const selectRecommendation = useCallback((recommendationId: string | null) => {
    setRequestedRecommendationId(recommendationId);
    replaceBayesianQuery({ recommendation_id: recommendationId });
  }, []);
  const recommendation = useBayesianRecommendationState({
    selectedStudyId: catalog.selectedStudyId,
    requestedRecommendationId,
    onRecommendationSelected: selectRecommendation,
  });
  const retention = useBayesianRetentionState(lifecycle.study);
  const study = lifecycle.study;
  const requestInFlight =
    lifecycle.isCreating ||
    lifecycle.isSavingTrial ||
    lifecycle.isClosing ||
    recommendation.isRecommending ||
    retention.isChecking ||
    retention.isDeleting;
  const studyActionDisabled =
    study === null ||
    study.status !== "active" ||
    requestInFlight ||
    lifecycle.pendingTransition !== null ||
    lifecycle.pendingStudyClose;
  const error =
    lifecycle.error ?? recommendation.error ?? retention.error ?? catalog.error;

  function selectStudy(studyId: string | null) {
    catalog.onSelect(studyId);
    setRequestedRecommendationId(null);
    setBuilderOpen(studyId === null);
    replaceBayesianQuery({ study_id: studyId, recommendation_id: null });
  }

  async function createStudy() {
    const payload = draft.buildRequest();
    if (typeof payload === "string") {
      lifecycle.setError(payload);
      return;
    }
    const created = await lifecycle.onCreate(payload);
    if (created === null) return;
    catalog.onSelect(created.study_id);
    catalog.onResetToFirstPage();
    draft.cancelSuccessor();
    setBuilderOpen(false);
    setRequestedRecommendationId(null);
    recommendation.clearRecommendation();
    replaceBayesianQuery({ study_id: created.study_id, recommendation_id: null });
  }

  async function confirmTrialTransition() {
    const updated = await lifecycle.confirmTrialTransition();
    if (updated) await recommendation.onRefresh();
  }

  async function createRecommendation() {
    if (study === null) return;
    const created = await recommendation.onRecommend(study);
    if (created) await lifecycle.refreshStudy();
  }

  async function closeStudy() {
    const closed = await lifecycle.confirmStudyClose();
    if (closed) catalog.onRefresh();
  }

  function prepareSuccessor() {
    if (study === null || study.status === "active") return;
    draft.prepareSuccessor(study);
    setBuilderOpen(true);
  }

  function handleDeleted() {
    lifecycle.clearStudy();
    recommendation.clearRecommendation();
    catalog.onSelect(null);
    catalog.onRefresh();
    setRequestedRecommendationId(null);
    setBuilderOpen(true);
    replaceBayesianQuery({ study_id: null, recommendation_id: null });
  }

  return (
    <section className="analysis-run-panel" aria-labelledby="bayesian-optimization-title">
      <div className="panel-heading">
        <div>
          <h3 id="bayesian-optimization-title">Bayesian 최적화</h3>
          <p>doe.bayesian_optimization · lifecycle별 전용 워크플로</p>
        </div>
        <span className="status-pill status-ready">전용 API</span>
      </div>
      <div className="info-box">
        앱은 목적함수를 실행하지 않습니다. 실제 실험 관측값만 입력하며, 추천 trial은 관측 전까지
        pending 상태입니다.
      </div>

      <BayesianStudyCatalog
        state={catalog}
        disabled={requestInFlight}
        onSelect={selectStudy}
        onCreateNew={() => {
          draft.cancelSuccessor();
          setBuilderOpen(true);
        }}
      />

      {builderOpen ? (
        <BayesianStudyBuilder
          draft={draft}
          isCreating={lifecycle.isCreating}
          disabled={requestInFlight}
          onCreate={() => void createStudy()}
          onCancel={() => {
            draft.cancelSuccessor();
            setBuilderOpen(false);
          }}
        />
      ) : null}

      {error !== null ? <BayesianError code={error} /> : null}
      {lifecycle.isRestoring || recommendation.isRestoring ? (
        <div className="notice-box" role="status">
          저장된 Study와 recommendation 관계를 확인하고 있습니다.
        </div>
      ) : null}

      {study !== null ? (
        <>
          <BayesianStudySummary study={study} />
          <BayesianTrialTable
            study={study}
            observations={lifecycle.observations}
            pendingTransition={lifecycle.pendingTransition}
            isSaving={lifecycle.isSavingTrial}
            actionsDisabled={studyActionDisabled}
            onObservationChange={lifecycle.setObservation}
            onRequestTransition={lifecycle.requestTrialTransition}
            onConfirmTransition={() => void confirmTrialTransition()}
            onCancelTransition={() => lifecycle.setPendingTransition(null)}
          />
          <BayesianRecommendationPanel
            study={study}
            recommendation={recommendation.recommendation}
            totalTrialBudget={recommendation.totalTrialBudget}
            isRecommending={recommendation.isRecommending}
            actionsDisabled={studyActionDisabled}
            onBudgetChange={recommendation.setTotalTrialBudget}
            onRecommend={() => void createRecommendation()}
          />
          <BayesianStudyClosePanel
            study={study}
            recommendation={recommendation.recommendation}
            target={lifecycle.closeTarget}
            reason={lifecycle.closeReason}
            note={lifecycle.closeNote}
            pending={lifecycle.pendingStudyClose}
            isClosing={lifecycle.isClosing}
            actionsDisabled={studyActionDisabled}
            onTargetChange={lifecycle.setCloseTarget}
            onReasonChange={lifecycle.setCloseReason}
            onNoteChange={lifecycle.setCloseNote}
            onRequestClose={() => lifecycle.setPendingStudyClose(true)}
            onConfirmClose={() => void closeStudy()}
            onCancelClose={() => lifecycle.setPendingStudyClose(false)}
            onPrepareSuccessor={prepareSuccessor}
          />
          <BayesianStudyDeletionPanel
            study={study}
            state={retention}
            disabled={requestInFlight}
            onDeleted={handleDeleted}
          />
        </>
      ) : null}
    </section>
  );
}

function BayesianError({ code }: { code: string }) {
  const details = getAnalysisRunErrorDetails(code);
  return (
    <div className="error-box" role="alert">
      <strong>{details.title}</strong>
      <p>{details.message}</p>
      <p>{details.action}</p>
      <span>오류 코드: {code}</span>
    </div>
  );
}

function replaceBayesianQuery(values: Record<string, string | null>) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  Object.entries(values).forEach(([key, value]) => {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  });
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}
