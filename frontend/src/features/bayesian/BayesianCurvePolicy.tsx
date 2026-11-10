import type { BayesianDesirabilityResponseGoal } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { curvePolicyMessages } from "../../i18n/boCurvePolicy";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import type { useBayesianStudyDraftState } from "./hooks/useBayesianStudyDraftState";

export function BayesianCurvePolicy({draft}: {draft: Pick<ReturnType<typeof useBayesianStudyDraftState>, "responseGoals" | "updateResponseGoal">}) {
  const {locale} = useI18n(), text = curvePolicyMessages(locale);
  return <section className="bo-curve-policy" aria-label={text.title}><p>{text.meaning}</p>
    {draft.responseGoals.filter(r => r.goal === "match_target").map(row => {
      const invalid = [row.lowerDesirability, row.upperDesirability].some(value => {
        const number = parseDoeResponseNumber(value ?? "");
        return number === null || number <= 0 || number >= 1;
      });
      return <fieldset key={row.key}><legend>{row.name}</legend><div className="option-grid bo-curve-fields">
        <label>{text.title}<select aria-label={`${row.name}: ${text.title}`} value={row.curve ?? "linear"}
          onChange={event => draft.updateResponseGoal(row.key, "curve", event.currentTarget.value === "gaussian_target" ? "gaussian_target" : "linear")}>
          <option value="linear">{text.linear}</option><option value="gaussian_target">{text.gaussian}</option>
        </select></label>
        {row.curve === "gaussian_target" && (["lower", "upper"] as const).map(side => {
          const field = side === "lower" ? "lowerDesirability" : "upperDesirability";
          return <label key={side}>{text[side]}<input inputMode="decimal" aria-label={`${row.name}: ${text[side]}`}
            value={row[field] ?? ""} onChange={event => draft.updateResponseGoal(row.key, field, event.currentTarget.value)} /></label>;
        })}
      </div>{row.curve === "gaussian_target" && invalid && <p role="status">{text.invalid}</p>}</fieldset>;
    })}
  </section>;
}

export function BayesianCurveSummary({responses}: {responses: BayesianDesirabilityResponseGoal[]}) {
  const {locale} = useI18n(), text = curvePolicyMessages(locale);
  return <div className="table-wrap"><table className="result-table"><caption>{text.stored}</caption>
    <thead><tr>{[text.response, text.policy, "d(L)", "d(T)", "d(H)"].map(t => <th scope="col" key={t}>{t}</th>)}</tr></thead>
    <tbody>{responses.map(r => <tr key={r.response_id}><th scope="row">{r.name}</th>
      <td>{r.curve ? text.gaussian : text.linear}</td><td>{exact(r.curve?.lower_desirability ?? (r.lower === null ? null : 0))}</td>
      <td>1</td><td>{exact(r.curve?.upper_desirability ?? (r.upper === null ? null : 0))}</td></tr>)}</tbody>
  </table></div>;
}
