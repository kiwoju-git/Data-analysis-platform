import { describe, expect, it } from "vitest";
import { parseDoeResponsePaste } from "./doeResponsePaste";

describe("factorial response paste", () => {
  it("maps one column by ascending run order without saving", () => {
    expect(parseDoeResponsePaste("94.1\n95.2\n", [2, 1], { layout: "values", hasHeader: false })).toEqual({
      ok: true, rows: [{ runOrder: 1, value: "94.1" }, { runOrder: 2, value: "95.2" }],
    });
  });
  it.each([",", "\t"])("maps shuffled explicit run orders using %j", (delimiter) => {
    const content = ["run_order,response", "2,-1.5", "1,2e3"].join("\n").split(",").join(delimiter);
    expect(parseDoeResponsePaste(content, [1, 2], { layout: "run_order", hasHeader: true })).toEqual({
      ok: true, rows: [{ runOrder: 1, value: "2e3" }, { runOrder: 2, value: "-1.5" }],
    });
  });
  it.each(["", "1", "1\n2\n3", "1\n\n2", "NaN\n1", "Infinity\n1", "1e999\n2", "0x10\n1", "1\t2\n3\t4", '"1\n2'])("rejects incomplete or invalid values %j", (content) => {
    expect(parseDoeResponsePaste(content, [1, 2], { layout: "values", hasHeader: false }).ok).toBe(false);
  });
  it.each(["1,2\n1,3", "1,2\n3,4", "1.1,2\n2,3", "run_order,run_order\n1,2\n2,3"])("rejects ambiguous run mapping %j", (content) => {
    expect(parseDoeResponsePaste(content, [1, 2], { layout: "run_order", hasHeader: content.startsWith("run_order") }).ok).toBe(false);
  });
  it("supports exactly 256 values without the dataset-preview 200-row cap", () => {
    const orders = Array.from({ length: 256 }, (_, index) => index + 1);
    const content = orders.join("\n");
    const result = parseDoeResponsePaste(content, orders, { layout: "values", hasHeader: false });
    expect(result.ok && result.rows.length).toBe(256);
    expect(parseDoeResponsePaste(content + "\n257", [...orders, 257], { layout: "values", hasHeader: false }).ok).toBe(false);
  });
});
