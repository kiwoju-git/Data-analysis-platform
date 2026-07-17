import { useEffect, useRef, useState } from "react";

import {
  deleteAttributeControlLimitSet,
  fetchAttributeControlLimitSets,
  fetchAttributeControlLimitSetDeletionPreflight,
  fetchAttributeControlMonitoringPreflight,
  type AttributeControlChartType,
  type AttributeControlLimitSetResponse,
  type AttributeControlLimitSetDeleteResponse,
  type AttributeControlLimitSetDeletionPreflightResponse,
  type AttributeControlMonitoringPreflightResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

export type AttributeControlPhase = "phase_1" | "phase_2";

export interface AttributeControlPhase2State {
  deletion: AttributeControlLimitSetDeleteResponse | null;
  deletionError: string | null;
  deletionPreflight: AttributeControlLimitSetDeletionPreflightResponse | null;
  error: string | null;
  isDeleting: boolean;
  isLoadingDeletionPreflight: boolean;
  isLoading: boolean;
  limitSets: AttributeControlLimitSetResponse[];
  preflight: AttributeControlMonitoringPreflightResponse | null;
  selectedLimitSet: AttributeControlLimitSetResponse | null;
  selectedLimitSetId: string | null;
  onSelectLimitSet: (limitSetId: string) => void;
  onClearDeletion: () => void;
  onDeleteLimitSet: (preflight: AttributeControlLimitSetDeletionPreflightResponse) => void;
  onLoadDeletionPreflight: () => void;
}

interface UseAttributeControlPhase2StateOptions {
  chartType: AttributeControlChartType;
  constantOpportunityConfirmed: boolean;
  countColumnId: string | null;
  denominatorColumnId: string | null;
  phase: AttributeControlPhase;
  targetDatasetVersionId: string | null;
}

export function useAttributeControlPhase2State({
  chartType,
  constantOpportunityConfirmed,
  countColumnId,
  denominatorColumnId,
  phase,
  targetDatasetVersionId,
}: UseAttributeControlPhase2StateOptions): AttributeControlPhase2State {
  const [limitSets, setLimitSets] = useState<AttributeControlLimitSetResponse[]>([]);
  const [selectedLimitSetId, setSelectedLimitSetId] = useState<string | null>(null);
  const [preflight, setPreflight] =
    useState<AttributeControlMonitoringPreflightResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletionPreflight, setDeletionPreflight] =
    useState<AttributeControlLimitSetDeletionPreflightResponse | null>(null);
  const [deletion, setDeletion] = useState<AttributeControlLimitSetDeleteResponse | null>(null);
  const [deletionError, setDeletionError] = useState<string | null>(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isPreflightLoading, setIsPreflightLoading] = useState(false);
  const [isLoadingDeletionPreflight, setIsLoadingDeletionPreflight] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const listRequest = useRef(createLatestRequestGuard()).current;
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionPreflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    listRequest.cancel();
    preflightRequest.cancel();
    deletionPreflightRequest.cancel();
    deletionRequest.cancel();
    setLimitSets([]);
    setSelectedLimitSetId(null);
    setPreflight(null);
    setError(null);
    setDeletionPreflight(null);
    setDeletionError(null);
    setIsListLoading(false);
    setIsPreflightLoading(false);
    setIsLoadingDeletionPreflight(false);
    setIsDeleting(false);
    if (phase !== "phase_2" || targetDatasetVersionId === null) {
      return;
    }
    const request = listRequest.begin();
    setIsListLoading(true);
    fetchAttributeControlLimitSets({ chartType, limit: 100 })
      .then((response) => {
        if (listRequest.isCurrent(request)) {
          setLimitSets(response.items);
        }
      })
      .catch((fetchError) => {
        if (listRequest.isCurrent(request)) {
          setError(
            fetchError instanceof Error
              ? fetchError.message
              : "attribute_control_limit_set_list_failed",
          );
        }
      })
      .finally(() => {
        if (listRequest.isCurrent(request)) {
          setIsListLoading(false);
        }
      });
  }, [
    chartType,
    deletionPreflightRequest,
    deletionRequest,
    listRequest,
    phase,
    preflightRequest,
    targetDatasetVersionId,
  ]);

  const selectedLimitSet =
    limitSets.find((candidate) => candidate.limit_set_id === selectedLimitSetId) ?? null;

  useEffect(() => {
    preflightRequest.cancel();
    setPreflight(null);
    setIsPreflightLoading(false);
    if (
      phase !== "phase_2" ||
      selectedLimitSet === null ||
      targetDatasetVersionId === null ||
      countColumnId === null ||
      (chartType !== "c" && denominatorColumnId === null)
    ) {
      return;
    }
    const request = preflightRequest.begin();
    setIsPreflightLoading(true);
    setError(null);
    fetchAttributeControlMonitoringPreflight(selectedLimitSet.limit_set_id, {
      target_dataset_version_id: targetDatasetVersionId,
      chart_type: chartType,
      count_definition: selectedLimitSet.count_definition,
      count_column_id: countColumnId,
      denominator_column_id: chartType === "c" ? null : denominatorColumnId,
      constant_opportunity_confirmed: constantOpportunityConfirmed,
    })
      .then((response) => {
        if (preflightRequest.isCurrent(request)) {
          setPreflight(response);
        }
      })
      .catch((fetchError) => {
        if (preflightRequest.isCurrent(request)) {
          setError(
            fetchError instanceof Error
              ? fetchError.message
              : "attribute_control_monitoring_preflight_failed",
          );
        }
      })
      .finally(() => {
        if (preflightRequest.isCurrent(request)) {
          setIsPreflightLoading(false);
        }
      });
  }, [
    chartType,
    constantOpportunityConfirmed,
    countColumnId,
    denominatorColumnId,
    phase,
    preflightRequest,
    selectedLimitSet,
    targetDatasetVersionId,
  ]);

  useEffect(() => {
    deletionPreflightRequest.cancel();
    deletionRequest.cancel();
    setDeletionPreflight(null);
    setDeletionError(null);
    setIsLoadingDeletionPreflight(false);
    setIsDeleting(false);
  }, [deletionPreflightRequest, deletionRequest, selectedLimitSetId]);

  return {
    deletion,
    deletionError,
    deletionPreflight,
    error,
    isDeleting,
    isLoading: isListLoading || isPreflightLoading,
    isLoadingDeletionPreflight,
    limitSets,
    preflight,
    selectedLimitSet,
    selectedLimitSetId,
    onSelectLimitSet: (limitSetId) => {
      setDeletion(null);
      setSelectedLimitSetId(limitSetId.length > 0 ? limitSetId : null);
    },
    onClearDeletion: () => {
      deletionPreflightRequest.cancel();
      deletionRequest.cancel();
      setDeletionPreflight(null);
      setDeletion(null);
      setDeletionError(null);
      setIsLoadingDeletionPreflight(false);
      setIsDeleting(false);
    },
    onLoadDeletionPreflight: () => {
      if (selectedLimitSet === null) return;
      const limitSetId = selectedLimitSet.limit_set_id;
      const request = deletionPreflightRequest.begin();
      setDeletionPreflight(null);
      setDeletion(null);
      setDeletionError(null);
      setIsLoadingDeletionPreflight(true);
      void fetchAttributeControlLimitSetDeletionPreflight(limitSetId)
        .then((response) => {
          if (deletionPreflightRequest.isCurrent(request)) {
            setDeletionPreflight(response);
          }
        })
        .catch((fetchError) => {
          if (deletionPreflightRequest.isCurrent(request)) {
            setDeletionError(
              fetchError instanceof Error
                ? fetchError.message
                : "attribute_control_limit_set_deletion_preflight_failed",
            );
          }
        })
        .finally(() => {
          if (deletionPreflightRequest.isCurrent(request)) {
            setIsLoadingDeletionPreflight(false);
          }
        });
    },
    onDeleteLimitSet: (currentPreflight) => {
      if (
        selectedLimitSet === null ||
        currentPreflight.limit_set_id !== selectedLimitSet.limit_set_id
      ) {
        return;
      }
      const limitSetId = selectedLimitSet.limit_set_id;
      const request = deletionRequest.begin();
      deletionPreflightRequest.cancel();
      preflightRequest.cancel();
      setDeletionError(null);
      setIsLoadingDeletionPreflight(false);
      setIsPreflightLoading(false);
      setIsDeleting(true);
      void deleteAttributeControlLimitSet(limitSetId, {
        confirmation_limit_set_id: limitSetId,
        expected_deletion_manifest_sha256:
          currentPreflight.deletion_manifest_sha256,
      })
        .then((response) => {
          if (deletionRequest.isCurrent(request)) {
            setDeletion(response);
            setDeletionPreflight(null);
            setPreflight(null);
            setLimitSets((current) =>
              current.filter((item) => item.limit_set_id !== limitSetId),
            );
            setSelectedLimitSetId(null);
          }
        })
        .catch((deleteError) => {
          if (deletionRequest.isCurrent(request)) {
            setDeletionError(
              deleteError instanceof Error
                ? deleteError.message
                : "attribute_control_limit_set_deletion_failed",
            );
          }
        })
        .finally(() => {
          if (deletionRequest.isCurrent(request)) setIsDeleting(false);
        });
    },
  };
}
