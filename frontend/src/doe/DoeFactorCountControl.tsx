import { useEffect, useId, useRef, useState } from "react";

import { useI18n } from "../i18n/LocaleProvider";

interface DoeFactorCountControlProps {
  availableCounts?: readonly number[];
  capabilityText?: string;
  count: number;
  disabled?: boolean;
  disabledReasonForCount?: (count: number) => string | null;
  factorLabels: readonly string[];
  maximum: number;
  minimum: number;
  onResize: (count: number) => void;
}

export function DoeFactorCountControl({
  availableCounts,
  capabilityText,
  count,
  disabled = false,
  disabledReasonForCount,
  factorLabels,
  maximum,
  minimum,
  onResize,
}: DoeFactorCountControlProps) {
  const { t } = useI18n();
  const controlId = useId();
  const dialogTitleId = useId();
  const [requestedCount, setRequestedCount] = useState(count);
  const [blockedReason, setBlockedReason] = useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<number | null>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => setRequestedCount(count), [count]);

  useEffect(() => {
    if (pendingRemoval === null) return;
    cancelRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPendingRemoval(null);
        return;
      }
      if (event.key !== "Tab") return;
      const first = cancelRef.current;
      const last = confirmRef.current;
      if (first === null || last === null) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [pendingRemoval]);

  const counts = availableCounts ?? Array.from(
    { length: maximum - minimum + 1 },
    (_value, index) => minimum + index,
  );
  const removedLabels = pendingRemoval === null
    ? []
    : factorLabels.slice(pendingRemoval, count);

  function applyCount() {
    setBlockedReason(null);
    if (requestedCount === count) return;
    const reason = disabledReasonForCount?.(requestedCount) ?? null;
    if (reason !== null) {
      setBlockedReason(reason);
      return;
    }
    if (requestedCount < count) {
      setPendingRemoval(requestedCount);
      return;
    }
    onResize(requestedCount);
  }

  return (
    <>
      <div className="doe-factor-count-control">
        <label htmlFor={controlId}>{t("doe.factorCount")}</label>
        <select
          id={controlId}
          disabled={disabled}
          value={requestedCount}
          onChange={(event) => setRequestedCount(Number(event.currentTarget.value))}
        >
          {counts.map((candidate) => (
            <option key={candidate} value={candidate}>{candidate}</option>
          ))}
        </select>
        <button
          className="secondary-button compact-button"
          disabled={disabled || requestedCount === count}
          type="button"
          onClick={applyCount}
        >
          {t("doe.applyFactorCount")}
        </button>
        {capabilityText === undefined ? null : <span>{capabilityText}</span>}
      </div>
      {blockedReason === null ? null : (
        <p className="field-error" role="alert">{blockedReason}</p>
      )}
      {pendingRemoval === null ? null : (
        <div className="confirmation-backdrop">
          <div
            aria-labelledby={dialogTitleId}
            aria-modal="true"
            className="confirmation-dialog"
            role="dialog"
          >
            <h3 id={dialogTitleId}>{t("doe.removeFactorsTitle")}</h3>
            <p>{t("doe.removeFactorsMessage", { count: count - pendingRemoval })}</p>
            <p>{t("doe.removedFactors", { factors: removedLabels.join(", ") })}</p>
            <div className="button-row">
              <button
                ref={cancelRef}
                className="secondary-button"
                type="button"
                onClick={() => setPendingRemoval(null)}
              >
                {t("doe.cancelResize")}
              </button>
              <button
                ref={confirmRef}
                className="danger-button"
                type="button"
                onClick={() => {
                  onResize(pendingRemoval);
                  setPendingRemoval(null);
                }}
              >
                {t("doe.confirmResize")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
