import { useEffect, useRef, useState, type FormEvent } from "react";
import { createLatestRequestGuard } from "./latestRequest";
import { usePastedDatasetDraft, type PastedDatasetDraftChangeReason } from "./usePastedDatasetDraft";

export function usePastedDatasetSubmission({ isSubmitting, onRegister, onDraftChange, resetRevision = 0 }: {
  isSubmitting: boolean;
  onRegister: (content: string, previewHasHeader: boolean) => Promise<boolean>;
  onDraftChange?: (dirty: boolean, reason: PastedDatasetDraftChangeReason) => void;
  resetRevision?: number;
}) {
  const [isAwaitingSubmit, setIsAwaitingSubmit] = useState(false);
  const requestGuard = useRef(createLatestRequestGuard());
  const draft = usePastedDatasetDraft((dirty, reason) => {
    if (reason === "user") {
      requestGuard.current.cancel();
      setIsAwaitingSubmit(false);
    }
    onDraftChange?.(dirty, reason);
  });
  const clearDraft = draft.clear;
  useEffect(() => {
    requestGuard.current.cancel();
    clearDraft(undefined, "reset");
    setIsAwaitingSubmit(false);
  }, [resetRevision, clearDraft]);
  useEffect(() => {
    const guard = requestGuard.current;
    return () => guard.cancel();
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.canSubmit || isSubmitting || isAwaitingSubmit) return;
    const request = requestGuard.current.begin();
    const revision = draft.getRevision();
    setIsAwaitingSubmit(true);
    try {
      const succeeded = await onRegister(draft.getRawText(), draft.hasHeaderPreview);
      if (requestGuard.current.isCurrent(request) && succeeded) draft.clear(revision, "reset");
    } finally {
      if (requestGuard.current.isCurrent(request)) setIsAwaitingSubmit(false);
    }
  };

  return { draft, isAwaitingSubmit, submit };
}
