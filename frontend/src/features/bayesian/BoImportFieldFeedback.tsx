import { CircleAlert } from "lucide-react";
import type { BoFieldFeedback } from "./boImportFieldSupport";
export function BoInlineFieldError({ feedback }: { feedback?: BoFieldFeedback }) {
  return feedback?.message ? <span id={`${feedback.id}-error`} className="bo-import-field-error">
    <CircleAlert size={14} aria-hidden="true" /><span>{feedback.message}</span>
  </span> : null;
}
