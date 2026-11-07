import type { BayesianCurrentBatchResponse, BayesianFactorResponse } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { formatInterval, formatMeasurement } from "../../statisticalNumberFormat";
import { boKernelLabel, savedBoKernelKind } from "./boKernelPolicy";
import { boText } from "./boNoisePolicy";

export function BayesianSurrogateSummary({ model, factors = [] }: {
  model: BayesianCurrentBatchResponse["shared_model"];
  factors?: readonly Pick<BayesianFactorResponse, "factor_id" | "name">[];
}) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const number = (value: number) => formatMeasurement(value, locale);
  const signal = model.signal_kernel;
  const factorIds = model.schema_version === 4 ? model.factor_ids : factors.map(factor => factor.factor_id);
  return <div className="bayesian-surrogate-summary">
    <p><strong>{text("저장된 신호 커널", "Saved signal kernel")}: </strong>{boKernelLabel(savedBoKernelKind(model))}</p>
    <details>
      <summary>{text("적합 매개변수", "Fitted parameters")}</summary>
      <div className="table-wrap"><table className="result-table"><tbody>
        <tr><th>{text("신호 분산 (표준화 Y)", "Signal variance (standardized Y)")}</th><td>{number(signal.amplitude)}</td></tr>
        <tr><th>{text("신호 분산 경계", "Signal variance bounds")}</th><td>{formatInterval({ lower: signal.amplitude_bounds[0], upper: signal.amplitude_bounds[1] }, locale)}</td></tr>
        <tr><th>{text("길이 척도 경계", "Length-scale bounds")}</th><td>{formatInterval({ lower: signal.length_scale_bounds[0], upper: signal.length_scale_bounds[1] }, locale)}</td></tr>
        {signal.length_scales.map((value, index) => {
          const id = factorIds[index];
          const name = factors.find(factor => factor.factor_id === id)?.name ?? id ?? `${index + 1}`;
          return <tr key={id ?? index}><th>{text("길이 척도", "Length scale")}: {name}</th><td>{number(value)}</td></tr>;
        })}
      </tbody></table></div>
      <p className="cell-subtext">{text("길이 척도는 요인 경계를 0~1로 정규화한 좌표의 값입니다. 커널 이름이 같아도 JMP와 동일한 적합 결과를 보장하지 않습니다.",
        "Length scales use factor coordinates normalized to 0-1. Matching kernel names do not establish identical JMP fits.")}</p>
      {model.schema_version === 4 ? <p className="cell-subtext"><code>{signal.kind === "constant_times_radial_ard" ? signal.convention : ""}</code></p> : null}
    </details>
  </div>;
}
