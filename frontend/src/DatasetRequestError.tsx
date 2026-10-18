import { RefreshCw } from "lucide-react";
import { useI18n } from "./i18n/LocaleProvider";
import { t } from "./i18n/translate";

export function DatasetRequestError({
  kind, error, busy = false, onRetry,
}: {
  kind: "preview" | "profile" | "activation";
  error: string | null;
  busy?: boolean;
  onRetry: () => void;
}) {
  const { locale } = useI18n();
  if (error === null) return null;
  return (
    <div className="error-box" role="alert" data-dataset-request-error={kind}>
      <p>{t(`dataset.workflow.${kind}Failed`, {}, locale)} <code>{error}</code></p>
      <button className="secondary-button" disabled={busy} onClick={onRetry} type="button">
        <RefreshCw aria-hidden="true" size={14} />
        {t(`dataset.workflow.retry.${kind}`, {}, locale)}
      </button>
    </div>
  );
}
