import { Plus, Trash2 } from "lucide-react";
import { useI18n } from "../../i18n/LocaleProvider";
import { boText } from "./boNoisePolicy";
import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";
import { BayesianTargetCurvePreview } from "./BayesianTargetCurvePreview";
import { desirabilityMessages } from "../../i18n/boDesirability";
import { BayesianCurvePolicy } from "./BayesianCurvePolicy";
import { curvePolicyMessages } from "../../i18n/boCurvePolicy";

type GoalEditor = Pick<ReturnType<typeof useBayesianStudyDraftState>, "responseGoals" | "updateResponseGoal" | "removeResponseGoal" | "addResponseGoal"> &
  Partial<Pick<ReturnType<typeof useBayesianStudyDraftState>, "studyName" | "factors" | "predecessorStudyId">>;
export function BayesianResponseGoals({ draft, sourceKey }: { draft: GoalEditor; sourceKey?: string }) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  return <section aria-label={text("반응별 목표", "Response goals")}>
    <p>{text("각 반응의 실제 단위로 기준을 정합니다. 최대화는 하한 < 목표값, 최소화는 목표값 < 상한, 목표값 맞추기는 하한 < 목표값 < 상한입니다.",
      "Set thresholds in each response's actual unit. Maximize: lower < target; minimize: target < upper; match target: lower < target < upper.")}</p>
    <div className="table-wrap"><table className="result-table bo-vector-goals">
      <caption>{curvePolicyMessages(locale).goals}</caption>
      <thead><tr>{[text("반응 이름", "Response name"), text("단위", "Unit"), text("목표", "Goal"),
        text("하한", "Lower"), text("목표값", "Target"), text("상한", "Upper"), text("중요도", "Importance"), text("삭제", "Remove")]
        .map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{draft.responseGoals.map((row, index) => <tr key={row.key} data-response-id={row.responseId}>
        {(["name", "unit"] as const).map(field => <td key={field}><input
          aria-label={`${text("반응", "Response")} ${index + 1} ${field === "name" ? text("이름", "name") : text("단위", "unit")}`}
          value={row[field]} maxLength={field === "name" ? 80 : 40}
          onChange={event => draft.updateResponseGoal(row.key, field, event.currentTarget.value)} /></td>)}
        <td><select aria-label={`${text("반응", "Response")} ${index + 1} ${text("목표", "goal")}`} value={row.goal}
          onChange={event => draft.updateResponseGoal(row.key, "goal", event.currentTarget.value as typeof row.goal)}>
          <option value="maximize">{text("최대화", "Maximize")}</option><option value="minimize">{text("최소화", "Minimize")}</option>
          <option value="match_target">{text("목표값 맞추기", "Match target")}</option>
        </select></td>
        {(["lower", "target", "upper", "importance"] as const).map(field => {
          const unused = (field === "lower" && row.goal === "minimize") || (field === "upper" && row.goal === "maximize");
          const label = { lower: text("하한", "lower"), target: text("목표값", "target"), upper: text("상한", "upper"), importance: text("중요도", "importance") }[field];
          return <td key={field}>{unused ? <span aria-label={text("해당 없음", "Not applicable")}>-</span> : <input inputMode="decimal"
            aria-label={`${text("반응", "Response")} ${index + 1} ${label}`} value={row[field]}
            onChange={event => draft.updateResponseGoal(row.key, field, event.currentTarget.value)} />}</td>;
        })}
        <td><button type="button" className="secondary-button" disabled={draft.responseGoals.length <= 1}
          aria-label={`${text("반응 삭제", "Remove response")} ${index + 1}`} title={text("반응 삭제", "Remove response")}
          onClick={() => draft.removeResponseGoal(row.key)}><Trash2 size={16} aria-hidden="true" /></button></td>
      </tr>)}</tbody>
    </table></div>
    <button type="button" className="secondary-button" disabled={draft.responseGoals.length >= 4} onClick={draft.addResponseGoal}>
      <Plus size={16} aria-hidden="true" /> {text("반응 추가", "Add response")}
    </button>
    <BayesianCurvePolicy draft={draft} />
    <div className="notice-box" role="status">{desirabilityMessages(locale).creationNotice}</div>
    <BayesianTargetCurvePreview goals={draft.responseGoals} sourceKey={sourceKey ?? JSON.stringify([draft.studyName, draft.factors, draft.responseGoals, draft.predecessorStudyId])} />
  </section>;
}
