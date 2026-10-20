import { t } from "../i18n/translate";
import { formatExactNumericValue, formatInterval, formatMeasurement } from "../statisticalNumberFormat";
import { ccdBoundsPreview, type CcdType } from "./rsmDesignDraft";
import { parseDoeResponseNumber } from "./doeResponsePaste";

export function CcdBoundsPreview({ factors, ccdType }: {
  factors: readonly { id: number; name: string; low: string; high: string; unit: string }[];
  ccdType: CcdType;
}) {
  return <div className="table-wrap"><table className="result-table">
    <thead><tr><th>{t("doe.rsm.factor")}</th><th>{t("doe.rsm.cubeRange")}</th><th>{t("doe.rsm.axialRange")}</th><th>{t("doe.rsm.center")}</th></tr></thead>
    <tbody>{factors.map((factor) => {
      const preview = ccdBoundsPreview(
        parseDoeResponseNumber(factor.low) ?? NaN, parseDoeResponseNumber(factor.high) ?? NaN, factors.length, ccdType,
      );
      return <tr key={factor.id}><td>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</td>
        <td>{preview ? <ExactRange lower={preview.factorialLow} upper={preview.factorialHigh} /> : "-"}</td>
        <td>{preview ? <ExactRange lower={preview.axialLow} upper={preview.axialHigh} /> : "-"}</td>
        <td>{formatMeasurement(preview?.center)}</td></tr>;
    })}</tbody>
  </table></div>;
}

function ExactRange({ lower, upper }: { lower: number; upper: number }) {
  return <details><summary>{formatInterval({ lower, upper })}</summary>
    <p>{t("doe.rsm.exactRange")}: [{formatExactNumericValue(lower)}, {formatExactNumericValue(upper)}]</p>
  </details>;
}
