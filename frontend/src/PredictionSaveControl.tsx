import type { SavedPredictionDescriptor } from "./api/types/reports";
import { useI18n } from "./i18n/LocaleProvider";

export function PredictionSaveControl({ checked, disabled, onChange, saved }: {
  checked: boolean; disabled: boolean; onChange: (value: boolean) => void; saved?: SavedPredictionDescriptor | null;
}) {
  const { t } = useI18n();
  const reference = saved?.source.prediction;
  return <div className="prediction-save-control">
    <label className="checkbox-field"><input type="checkbox" checked={checked} disabled={disabled}
      data-save-completed-prediction onChange={(event) => onChange(event.currentTarget.checked)} />{t("prediction.saveCompleted")}</label>
    <p className="field-help">{t("prediction.saveCompletedHelp")}</p>
    {saved !== undefined && saved !== null ? <div className="notice-box" role="status" data-saved-prediction>
      {t("prediction.savedCompleted")} {reference?.storage === "completed_prediction" ? <code>{reference.prediction_artifact_id}</code> : null}
      {" "}<a href="/reports?source_kind=regression_prediction">{t("prediction.openSaved")}</a>
    </div> : null}
  </div>;
}
