import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { GpOptimizationSettings, gpLengthPreset, gpLengthValue } from "./GpOptimizationSettings";

describe("GPR explicit length coordinates", () => {
  it("proposes standardized smoothing and preserves an explicit legacy preset", () => {
    expect(gpLengthPreset(true).lower).toBe("0.5");
    expect(gpLengthPreset(true, true).lower).toBe("0.01");
    expect(gpLengthValue(gpLengthPreset(false), false, "l_bfgs_b")?.coordinate_system).toBe("original");
  });
  it("rejects blanks, nonfinite values, inverted bounds and BFGS boundary starts", () => {
    for (const lower of ["", " ", "NaN", "Infinity", "0", "-1", "101"]) {
      expect(gpLengthValue({ ...gpLengthPreset(true), lower }, true, "l_bfgs_b")).toBeNull();
    }
    expect(gpLengthValue({ lower: "1", initial: "1", upper: "100" }, true, "bfgs")).toBeNull();
    expect(gpLengthValue({ lower: "1", initial: "1", upper: "100" }, true, "l_bfgs_b")).not.toBeNull();
  });
  it("uses labelled controls and explanatory coordinate text", () => {
    const html = renderToString(<GpOptimizationSettings draft={gpLengthPreset(true)} onChange={() => undefined}
      optimizer="bfgs" onOptimizerChange={() => undefined} standardized />);
    expect(html).toContain("ddof=1");
    expect(html).toContain("BFGS");
    expect(html).toContain('aria-describedby="gp-length-coordinate-help gp-length-validation"');
    expect(html).not.toContain("ADAM");
  });
});
