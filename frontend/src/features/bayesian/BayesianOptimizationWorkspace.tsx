import { useCallback, useMemo, useState } from "react";

import { getAnalysisRunErrorDetails } from "../../analysisRunErrors";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixedMessages } from "../../i18n/boMixed";
import { BayesianMixedStudyBuilder } from "./BayesianMixedStudyBuilder";
import { BayesianMixedStudyWorkspace } from "./BayesianMixedStudyWorkspace";
import { BayesianMixedPlanningPanel } from "./BayesianMixedPlanningPanel";
import { BayesianMixedSavedBatch } from "./BayesianMixedSavedBatch";
import { BayesianRecommendationPanel } from "./BayesianRecommendationPanel";
import { BayesianStudyBuilder } from "./BayesianStudyBuilder";
import { BayesianStudyCatalog } from "./BayesianStudyCatalog";
import { BayesianStudyClosePanel } from "./BayesianStudyClosePanel";
import { BayesianStudyDeletionPanel } from "./BayesianStudyDeletionPanel";
import { BayesianStudySummary } from "./BayesianStudySummary";
import { BayesianVectorStudySnapshot } from "./BayesianVectorStudySnapshot";
import { BayesianVectorObservationEntry } from "./BayesianVectorObservationEntry";
import { BayesianDesirabilityRecommendationPanel } from "./BayesianDesirabilityRecommendationPanel";
import { BayesianPlanningPanel } from "./BayesianPlanningPanel";
import { BayesianPlanningSavedBatch } from "./BayesianPlanningSavedBatch";
import { BayesianAugmentationPanel, type AugmentationManualSeed } from "./BayesianAugmentationPanel";
import { BayesianAugmentationSavedBatch } from "./BayesianAugmentationSavedBatch";
import { buildDesirabilityRequest } from "./bayesianDesirabilityDraft";
import { useBayesianDesirabilityRecommendation } from "./hooks/useBayesianDesirabilityRecommendation";
import { BayesianTrialTable } from "./BayesianTrialTable";
import { BayesianReplicatePanel } from "./BayesianReplicatePanel";
import { useBayesianReplicateState } from "./hooks/useBayesianReplicateState";
import { validBayesianId } from "./bayesianDisplay";
import { bayesianReviewErrorDetails } from "./bayesianReviewErrors";
import { boText } from "./boNoisePolicy";
import { useBayesianRecommendationState } from "./hooks/useBayesianRecommendationState";
import { useBayesianRetentionState } from "./hooks/useBayesianRetentionState";
import { useBayesianStudyCatalogState } from "./hooks/useBayesianStudyCatalogState";
import { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";
import { useBayesianStudyLifecycleState } from "./hooks/useBayesianStudyLifecycleState";

export function BayesianOptimizationWorkspace() {
  const { locale } = useI18n(), mixedText = mixedMessages(locale);
  const initialQuery = useMemo(
    () => new URLSearchParams(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialStudyId = validBayesianId(initialQuery.get("study_id"));
  const initialRecommendationId = validBayesianId(initialQuery.get("recommendation_id"));
  const initialBatchId = validBayesianId(initialQuery.get("batch_id"));
  const initialPlanningBatchId = validBayesianId(initialQuery.get("planning_batch_id"));
  const initialAugmentationBatchId = validBayesianId(initialQuery.get("augmentation_batch_id"));
  const initialMixedBatchId = validBayesianId(initialQuery.get("mixed_planning_batch_id"));
  const recommendationQueryConflict =
    [initialRecommendationId, initialBatchId, initialPlanningBatchId, initialAugmentationBatchId, initialMixedBatchId].filter(value => value !== null).length > 1 ||
    (initialQuery.has("planning_batch_id") && initialPlanningBatchId === null) ||
    (initialQuery.has("augmentation_batch_id") && initialAugmentationBatchId === null) ||
    (initialQuery.has("mixed_planning_batch_id") && initialMixedBatchId === null);
  const [requestedRecommendationId, setRequestedRecommendationId] =
    useState(recommendationQueryConflict ? null : initialRecommendationId);
  const [requestedBatchId, setRequestedBatchId] = useState(
    recommendationQueryConflict ? null : initialBatchId,
  );
  const [requestedPlanningBatchId, setRequestedPlanningBatchId] = useState(recommendationQueryConflict ? null : initialPlanningBatchId);
  const [planningConfirming, setPlanningConfirming] = useState(false);
  const [augmentationConfirming, setAugmentationConfirming] = useState(false);
  const [requestedAugmentationBatchId, setRequestedAugmentationBatchId] = useState(recommendationQueryConflict ? null : initialAugmentationBatchId);
  const [manualSeed, setManualSeed] = useState<AugmentationManualSeed | null>(null);
  const [requestedMixedBatchId, setRequestedMixedBatchId] = useState(recommendationQueryConflict ? null : initialMixedBatchId);
  const [mixedBusy, setMixedBusy] = useState(false), [mixedConfirming, setMixedConfirming] = useState(false), [mixedCreating, setMixedCreating] = useState(false);
  const [builderMode, setBuilderMode] = useState<"numeric" | "mixed">("numeric");
  const [builderOpen, setBuilderOpen] = useState(initialStudyId === null);
  const catalog = useBayesianStudyCatalogState(initialStudyId);
  const draft = useBayesianStudyDraftState();
  const lifecycle = useBayesianStudyLifecycleState(catalog.selectedStudyId);
  const selectRecommendation = useCallback((recommendationId: string | null) => {
    setRequestedRecommendationId(recommendationId);
    setRequestedBatchId(null);
    setRequestedPlanningBatchId(null);
    setRequestedAugmentationBatchId(null);
    setRequestedMixedBatchId(null);
    replaceBayesianQuery({
      batch_id: null,
      planning_batch_id: null,
      augmentation_batch_id: null,
      recommendation_id: recommendationId,
    });
  }, []);
  const selectBatch = useCallback((batchId: string | null) => {
    setRequestedBatchId(batchId);
    setRequestedRecommendationId(null);
    setRequestedPlanningBatchId(null);
    setRequestedAugmentationBatchId(null);
    setRequestedMixedBatchId(null);
    replaceBayesianQuery({
      batch_id: batchId,
      planning_batch_id: null,
      augmentation_batch_id: null,
      recommendation_id: null,
    });
  }, []);
  const selectPlanningBatch = useCallback((batchId: string) => {
    setRequestedMixedBatchId(null);
    setRequestedPlanningBatchId(batchId); setRequestedAugmentationBatchId(null); setRequestedBatchId(null); setRequestedRecommendationId(null);
    replaceBayesianQuery({ planning_batch_id: batchId, augmentation_batch_id: null, batch_id: null, recommendation_id: null });
  }, []);
  const selectAugmentationBatch = useCallback((batchId: string) => {
    setRequestedMixedBatchId(null);
    setRequestedAugmentationBatchId(batchId); setRequestedPlanningBatchId(null); setRequestedBatchId(null); setRequestedRecommendationId(null);
    replaceBayesianQuery({ augmentation_batch_id: batchId, planning_batch_id: null, batch_id: null, recommendation_id: null });
  }, []);
  const study =
    lifecycle.study?.study_id === catalog.selectedStudyId ? lifecycle.study : null;
  const mixedStudy = lifecycle.mixedStudy?.study_id === catalog.selectedStudyId ? lifecycle.mixedStudy : null;
  const scalarStudy = study?.objective.goal_type !== "desirability" ? study : null;
  const recommendation = useBayesianRecommendationState({
    selectedStudyId: scalarStudy?.study_id ?? null,
    sourceHistoryKey: scalarStudy === null ? null : `${scalarStudy.study_id}:${scalarStudy.observation_history.history_revision_id}:${scalarStudy.observation_history.observation_history_sha256}`,
    requestedBatchId,
    requestedRecommendationId,
    onBatchSelected: selectBatch,
    onRecommendationSelected: selectRecommendation,
  });
  const desirability = useBayesianDesirabilityRecommendation({
    study: study?.objective.goal_type === "desirability" ? study : null,
    requestedBatchId,
    onBatchSelected: selectBatch,
  });
  const planningFit = useMemo(() => study?.objective.goal_type === "desirability"
    ? buildDesirabilityRequest(study, desirability.draft, "planning").request : null,
  [study, desirability.draft]);
  const selectedRecommendation =
    recommendation.recommendation?.study_id === catalog.selectedStudyId
      ? recommendation.recommendation
      : null;
  const selectedBatch =
    recommendation.batch?.study_id === catalog.selectedStudyId
      ? recommendation.batch
      : null;
  const retention = useBayesianRetentionState(study ?? mixedStudy);
  const replicates = useBayesianReplicateState(study);
  const requestInFlight =
    catalog.isLoading ||
    lifecycle.isRestoring ||
    lifecycle.isCreating ||
    lifecycle.isSavingTrial ||
    lifecycle.isClosing ||
    recommendation.isRestoring ||
    recommendation.isRecommending ||
    recommendation.isConfirming ||
    desirability.isRestoring ||
    desirability.isReviewing ||
    desirability.isConfirming ||
    planningConfirming ||
    augmentationConfirming ||
    mixedBusy || mixedConfirming || mixedCreating ||
    replicates.isRunning ||
    retention.isChecking ||
    retention.isDeleting;
  const studyActionDisabled =
    study === null ||
    study.status !== "active" ||
    requestInFlight ||
    lifecycle.pendingTransition !== null ||
    lifecycle.pendingObservationBatch ||
    lifecycle.pendingStudyClose;
  const error =
    (recommendationQueryConflict
      ? "bayesian_recommendation_query_conflict"
      : null) ??
    ((study !== null && requestedMixedBatchId !== null) || (mixedStudy !== null && [requestedRecommendationId, requestedBatchId, requestedPlanningBatchId, requestedAugmentationBatchId].some(value => value !== null))
      ? "bayesian_recommendation_query_conflict" : null) ??
    lifecycle.error ??
    recommendation.error ??
    retention.error ??
    catalog.error;

  function selectStudy(studyId: string | null) {
    catalog.onSelect(studyId);
    setRequestedRecommendationId(null);
    setRequestedBatchId(null);
    setRequestedPlanningBatchId(null);
    setRequestedAugmentationBatchId(null); setManualSeed(null);
    setRequestedMixedBatchId(null);
    setBuilderOpen(studyId === null);
    replaceBayesianQuery({
      study_id: studyId,
      batch_id: null,
      planning_batch_id: null,
      augmentation_batch_id: null,
      recommendation_id: null,
    });
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
    setRequestedBatchId(null);
    setRequestedPlanningBatchId(null);
    setRequestedAugmentationBatchId(null); setManualSeed(null);
    setRequestedMixedBatchId(null);
    recommendation.clearRecommendation();
    replaceBayesianQuery({
      study_id: created.study_id,
      batch_id: null,
      planning_batch_id: null,
      augmentation_batch_id: null,
      recommendation_id: null,
    });
  }

  async function confirmTrialTransition() {
    const updated = await lifecycle.confirmTrialTransition();
    if (updated) await recommendation.onRefresh();
  }

  async function confirmObservationBatch() {
    const updated = await lifecycle.confirmObservationBatch();
    if (updated) await recommendation.onRefresh();
  }

  async function createRecommendation() {
    if (study === null) return;
    await recommendation.onRecommend(study);
  }

  async function confirmRecommendation() {
    if (study === null) return;
    const created = await recommendation.onConfirmReview(study);
    if (created) await lifecycle.refreshStudy();
  }

  async function confirmDesirability() {
    if (await desirability.confirm()) await lifecycle.refreshStudy();
  }

  async function refreshDesirability() {
    await lifecycle.refreshStudy();
    desirability.refresh();
  }
  function planningConfirmed(batchId: string) {
    selectPlanningBatch(batchId);
    void lifecycle.refreshStudy();
    void catalog.onRefresh();
  }
  function augmentationConfirmed(batchId: string) {
    selectAugmentationBatch(batchId);
    void lifecycle.refreshStudy();
    void catalog.onRefresh();
  }
  function mixedConfirmed(batchId: string) {
    setRequestedMixedBatchId(batchId); setRequestedAugmentationBatchId(null); setRequestedPlanningBatchId(null); setRequestedBatchId(null); setRequestedRecommendationId(null);
    replaceBayesianQuery({ mixed_planning_batch_id: batchId, augmentation_batch_id: null, planning_batch_id: null, batch_id: null, recommendation_id: null });
    void lifecycle.refreshStudy(); void catalog.onRefresh();
  }

  async function createReplicates(retry = false) {
    const created = await replicates.submit(recommendation.totalTrialBudget, retry);
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
    setRequestedBatchId(null);
    setRequestedPlanningBatchId(null);
    setRequestedAugmentationBatchId(null); setManualSeed(null);
    setRequestedMixedBatchId(null);
    setBuilderOpen(true);
    replaceBayesianQuery({
      study_id: null,
      batch_id: null,
      planning_batch_id: null,
      augmentation_batch_id: null,
      recommendation_id: null,
    });
  }

  return (
    <section className="analysis-run-panel" aria-label="Bayesian 최적화 Study 작업">
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

      {builderOpen && <label>{mixedText.studyMode}<select aria-label={mixedText.studyMode} disabled={requestInFlight} value={builderMode} onChange={event => setBuilderMode(event.currentTarget.value as "numeric" | "mixed")}><option value="numeric">{mixedText.numericMode}</option><option value="mixed">{mixedText.mixedMode}</option></select></label>}
      {builderOpen && builderMode === "mixed" && <BayesianMixedStudyBuilder ownerKey={`mixed-builder:${catalog.selectedStudyId ?? "new"}`} disabled={requestInFlight}
        onBusyChange={setMixedCreating} onCancel={() => setBuilderOpen(false)} onCreated={created => { selectStudy(created.study_id); setBuilderOpen(false); catalog.onResetToFirstPage(); }} />}
      {builderOpen && builderMode === "numeric" ? (
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

      {mixedStudy !== null && <>
        <BayesianMixedStudyWorkspace study={mixedStudy} disabled={requestInFlight} onCommitted={lifecycle.acceptMixedCommit} onRefresh={() => { void lifecycle.refreshStudy(); void catalog.onRefresh(); }} onBusyChange={setMixedBusy} />
        <BayesianMixedPlanningPanel study={mixedStudy} disabled={requestInFlight} onConfirmed={mixedConfirmed} onConfirmingChange={setMixedConfirming} />
        {requestedMixedBatchId !== null && <BayesianMixedSavedBatch study={mixedStudy} batchId={requestedMixedBatchId} />}
        <BayesianStudyDeletionPanel study={mixedStudy} state={retention} disabled={requestInFlight} onDeleted={handleDeleted} />
      </>}

      {error !== null ? <BayesianError code={error} /> : null}
      {lifecycle.isRestoring || recommendation.isRestoring ? (
        <div className="notice-box" role="status">
          저장된 Study와 recommendation 관계를 확인하고 있습니다.
        </div>
      ) : null}

      {study !== null ? (
        <>
          {study.objective.goal_type === "desirability" ? (
            <>
            <BayesianVectorStudySnapshot study={study} />
            <BayesianVectorObservationEntry key={study.study_id} study={study}
              onCommitted={lifecycle.acceptVectorCommit} onRefresh={() => void lifecycle.refreshStudy()} disabled={requestInFlight} />
            <BayesianDesirabilityRecommendationPanel study={study} state={desirability}
              disabled={catalog.isLoading || lifecycle.isRestoring || lifecycle.isSavingTrial || retention.isDeleting || retention.isChecking || planningConfirming || augmentationConfirming}
              onConfirm={() => void confirmDesirability()} onRefresh={() => void refreshDesirability()} />
            <BayesianPlanningPanel study={study} fitRequest={planningFit} disabled={requestInFlight}
              onConfirmed={planningConfirmed} onConfirmingChange={setPlanningConfirming} manualSeed={manualSeed} />
            <BayesianAugmentationPanel study={study} disabled={requestInFlight} onConfirmed={augmentationConfirmed}
              onConfirmingChange={setAugmentationConfirming} onManual={setManualSeed} />
            {requestedPlanningBatchId !== null && <BayesianPlanningSavedBatch study={study} batchId={requestedPlanningBatchId} />}
            {requestedAugmentationBatchId !== null && <BayesianAugmentationSavedBatch study={study} batchId={requestedAugmentationBatchId} />}
            </>
          ) : <>
          <BayesianStudySummary study={study} />
          <BayesianTrialTable
            study={study}
            observations={lifecycle.observations}
            pendingTransition={lifecycle.pendingTransition}
            pendingObservationBatch={lifecycle.pendingObservationBatch}
            isSaving={lifecycle.isSavingTrial}
            actionsDisabled={studyActionDisabled}
            onObservationChange={lifecycle.setObservation}
            onObservationBatchApply={lifecycle.setObservations}
            onRequestTransition={lifecycle.requestTrialTransition}
            onRequestObservationBatch={lifecycle.requestObservationBatch}
            onConfirmTransition={() => void confirmTrialTransition()}
            onConfirmObservationBatch={() => void confirmObservationBatch()}
            onCancelTransition={() => lifecycle.setPendingTransition(null)}
            onCancelObservationBatch={() => lifecycle.setPendingObservationBatch(false)}
          />
          <BayesianReplicatePanel study={study} state={replicates} disabled={studyActionDisabled}
            totalBudget={recommendation.totalTrialBudget} onSubmit={retry => void createReplicates(retry)}
            onRefresh={() => void lifecycle.refreshStudy()} />
          <BayesianRecommendationPanel
            study={study}
            batch={selectedBatch}
            recommendation={selectedRecommendation}
            executionMode={recommendation.executionMode}
            batchSize={recommendation.batchSize}
            explorationProfile={recommendation.explorationProfile}
            customXi={recommendation.customXi}
            totalTrialBudget={recommendation.totalTrialBudget}
            isRecommending={recommendation.isRecommending}
            isConfirming={recommendation.isConfirming}
            review={recommendation.review?.study_id === study.study_id ? recommendation.review : null}
            onConfirmReview={() => void confirmRecommendation()}
            onDiscardReview={recommendation.discardReview}
            actionsDisabled={studyActionDisabled}
            onExecutionModeChange={recommendation.onExecutionModeChange}
            onBatchSizeChange={recommendation.setBatchSize}
            onExplorationProfileChange={
              recommendation.setExplorationProfile
            }
            onCustomXiChange={recommendation.setCustomXi}
            onBudgetChange={recommendation.setTotalTrialBudget}
            onRecommend={() => void createRecommendation()}
            noiseDraft={recommendation.noiseDraft}
            kernelKind={recommendation.kernelKind}
            onKernelKindChange={recommendation.onKernelKindChange}
            onNoiseDraftChange={recommendation.onNoiseDraftChange}
            draftChanged={recommendation.draftChanged}
          />
          <BayesianStudyClosePanel
            study={study}
            hasRecommendation={
              selectedRecommendation !== null || selectedBatch !== null
            }
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
          </>}
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
  const { locale } = useI18n();
  const details = bayesianReviewErrorDetails(code, locale) ?? getAnalysisRunErrorDetails(code, locale);
  return (
    <div className="error-box" role="alert">
      <strong>{details.title}</strong>
      <p>{details.message}</p>
      <p>{details.action}</p>
      <span>{boText(locale, "오류 코드", "Error code")}: {code}</span>
    </div>
  );
}

function replaceBayesianQuery(values: Record<string, string | null>) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (!("mixed_planning_batch_id" in values)) url.searchParams.delete("mixed_planning_batch_id");
  Object.entries(values).forEach(([key, value]) => {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  });
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}
