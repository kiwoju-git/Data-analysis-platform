export interface BoFieldFeedback { id: string; message?: string }

export function boFieldProps(feedback?: BoFieldFeedback) {
  return {
    id: feedback?.id,
    "aria-invalid": feedback?.message ? true as const : undefined,
    "aria-describedby": feedback?.message ? `${feedback.id}-error` : undefined,
  };
}

export function focusBoImportField(element: HTMLElement | null) {
  if (!element || element.matches(":disabled")) return;
  let parent: HTMLElement | null = element.parentElement;
  while (parent) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
    parent = parent.parentElement;
  }
  element.focus();
}
