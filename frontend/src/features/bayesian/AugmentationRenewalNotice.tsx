import { FolderOpen, RefreshCw } from "lucide-react";
import type { AugmentationRenewalLineage } from "../../api/types/boAugmentation";
import { useI18n } from "../../i18n/LocaleProvider";
import { renewalMessages } from "../../i18n/boRenewal";

export function AugmentationRenewalNotice({ required, lineage, confirmed, disabled, onRenew, onOpenOriginal }: {
  required: boolean; lineage: AugmentationRenewalLineage | null; confirmed: boolean; disabled: boolean;
  onRenew: () => void; onOpenOriginal: (id: string) => void;
}) {
  const { locale } = useI18n(), text = renewalMessages(locale);
  if (required && !confirmed) return <div className="notice-box notice-warning">
    <p role="status">{text.required}</p>
    <button className="secondary-button" type="button" disabled={disabled} onClick={onRenew}>
      <RefreshCw size={16} aria-hidden="true" />{text.renew}
    </button>
  </div>;
  if (!lineage) return null;
  return <section aria-label={text.lineage}>
    {!confirmed && <p role="status">{text.renewed}</p>}<p>{text.explanation}</p>
    <details><summary>{text.lineage}</summary><dl className="bo-planning-source">
      <div><dt>{text.original}</dt><dd>{lineage.original_selection_id}</dd></div>
      <div><dt>Config SHA-256</dt><dd>{lineage.original_config_sha256}</dd></div>
      <div><dt>Result SHA-256</dt><dd>{lineage.original_result_sha256}</dd></div>
    </dl></details>
    <button className="secondary-button" type="button" onClick={() => onOpenOriginal(lineage.original_selection_id)}>
      <FolderOpen size={16} aria-hidden="true" />{text.original}
    </button>
  </section>;
}
