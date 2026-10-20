import { useState } from "react";
import type { FactorialDesignResponse } from "../api/types/doe";
import { t } from "../i18n/translate";
import { aliasEquation, visibleAliasClasses } from "./aliasPresentation";
import "./doeAnalysisPresentation.css";

export function FractionalAliasSummary({ design }: {
  design: Pick<FactorialDesignResponse, "design_id" | "factors" | "fractional">;
}) {
  const [allOrders, setAllOrders] = useState(false);
  const metadata = design.fractional;
  if (!metadata) return null;
  const classes = visibleAliasClasses(metadata, allOrders ? null : 2);
  const total = metadata.alias_classes?.length ?? 0;
  return <section className="result-section fractional-alias-summary">
    <h3>{t("doe.alias.title")}</h3>
    <div className="metadata-grid">
      <span>Fraction</span><strong>{metadata.fraction}</strong>
      <span>Resolution</span><strong>{({ 3: "III", 4: "IV", 5: "V", 6: "VI" } as Record<number, string>)[metadata.resolution] ?? metadata.resolution}</strong>
      <span>Generator</span><strong>{metadata.generators.join(", ")}</strong>
      <span>Defining relation</span><strong>{metadata.defining_relation.join(" = ")}</strong>
    </div>
    <details open className="doe-alias-names">
      <summary>{t("doe.alias.symbolMap")}</summary>
      <div className="table-wrap"><table className="result-table">
        <thead><tr><th>{t("doe.alias.symbol")}</th><th>{t("doe.alias.factor")}</th><th>{t("doe.alias.unit")}</th></tr></thead>
        <tbody>{design.factors.map((factor, index) => <tr key={`${design.design_id}:factor:${index}`}>
          <td>{String.fromCharCode(65 + index)}</td><td>{factor.name}</td><td>{factor.unit ?? "-"}</td>
        </tr>)}</tbody>
      </table></div>
    </details>
    <p>{t("doe.alias.identity")}</p>
    <label className="doe-table-toggle"><input type="checkbox" checked={allOrders}
      onChange={(event) => setAllOrders(event.currentTarget.checked)} />
      <span>{t("doe.alias.allOrders")}</span>
    </label>
    {classes ? <>
      <p>{t("doe.alias.scope", { visible: classes.length, total })}</p>
      <div className="table-wrap"><table className="result-table">
        <thead><tr><th>{t("doe.alias.class")}</th><th>{t("doe.alias.fullNames")}</th></tr></thead>
        <tbody>{classes.map(({ id, terms }) => <tr key={`${design.design_id}:${id}`}>
          <td><code>{aliasEquation(terms)}</code></td>
          <td><details><summary>{t("doe.alias.fullNames")}</summary><p>{aliasEquation(terms, true)}</p></details></td>
        </tr>)}</tbody>
      </table></div>
    </> : <div className="table-wrap"><table className="result-table">
      <thead><tr><th>{t("doe.alias.legacy")}</th></tr></thead>
      <tbody>{metadata.alias_groups.map((group, index) => <tr key={`${design.design_id}:legacy:${index}`}>
        <td>{group.join(" = ")}</td>
      </tr>)}</tbody>
    </table></div>}
    <p className="notice-box notice-warning">{t("doe.alias.interpretation")}</p>
  </section>;
}
