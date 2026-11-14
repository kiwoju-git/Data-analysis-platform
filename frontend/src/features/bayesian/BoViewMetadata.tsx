import type { BoViewPayload } from "../../api/boViews";
import { useI18n } from "../../i18n/LocaleProvider";
import { boViewMessages } from "../../i18n/boViews";
import { planningMessages } from "../../i18n/boPlanning";

export function BoViewMetadata({ payload }: { payload: BoViewPayload }) {
  const { locale } = useI18n(), text = boViewMessages(locale);
  const planning = planningMessages(locale);
  const meanings: Record<string, string> = {
    bayesian_optimization_model_convergence_warning: planning.convergenceWarning,
    bayesian_surrogate_signal_bound: planning.signalBoundWarning,
    bayesian_surrogate_noise_bound: planning.noiseBoundWarning,
    bayesian_optimization_constant_objective: planning.constantWarning,
  };
  if (payload.kind !== "profiler_matrix") return null;
  return <>{payload.warnings.length > 0 && <aside className="notice-box notice-warning" aria-label={text.warnings}><strong>{text.warnings}</strong><p>{text.warningMeaning}</p><ul>{payload.warnings.map((warning, index) => <li key={`${index}:${warning}`}>{meanings[warning] ?? planning.unknownWarning} <code>{warning}</code></li>)}</ul></aside>}
    {payload.axes.some(axis => axis.available_level_count !== null) && <details><summary>{text.levels}</summary><dl className="bo-planning-source">{payload.axes.filter(axis => axis.available_level_count !== null).map(axis => <div key={axis.factor_id}><dt>{axis.name}: {text.sample}</dt><dd>{axis.points.length} / {axis.available_level_count}</dd></div>)}</dl></details>}
  </>;
}
