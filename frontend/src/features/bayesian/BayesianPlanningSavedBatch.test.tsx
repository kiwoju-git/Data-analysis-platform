import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { PlanningSavedBatchDetails } from "./BayesianPlanningSavedBatch";
import { planningBatchFixture } from "./boPlanning.fixture";

describe("exact saved manual batch presentation", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["en", "ko"] as const)("shows source, saved predictions and current trial state in %s", locale => {
    setCurrentLocale(locale); const { batch, study } = planningBatchFixture();
    const before = JSON.stringify(batch);
    const html = renderToStaticMarkup(<PlanningSavedBatchDetails batch={batch} study={study} />);
    expect(html).toContain(batch.batch_id); expect(html).toContain(batch.source.model_sha256);
    expect(html).toContain(batch.source.rows_sha256); expect(html).toContain(batch.result_sha256);
    expect(html).toContain(locale === "en" ? "Current trial state" : "현재 실험 상태");
    expect(html).toContain(locale === "en" ? "Latent SD" : "잠재 SD");
    expect(html).toContain(locale === "en" ? "New-measurement predictive SD" : "새 측정 예측 SD");
    expect(html).toContain("Yield &lt;raw&gt;"); expect(html).toContain("1e-8");
    expect(html).not.toContain("<input"); expect(JSON.stringify(batch)).toBe(before);
  });
});
