import { expect, it, vi } from "vitest";
import { copyDoeEquation } from "./copyDoeEquation";

it("copies exact equation text only after the requested action", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  expect(await copyDoeEquation("Y = 1e-6 + 2 * 한글", () => ({ writeText }))).toBe(true);
  expect(writeText).toHaveBeenCalledExactlyOnceWith("Y = 1e-6 + 2 * 한글");
});
it("offers manual copy for unavailable, rejected and throwing clipboard access", async () => {
  expect(await copyDoeEquation("Y = 0", () => undefined)).toBe(false);
  expect(await copyDoeEquation("Y = 0", () => { throw new Error("SecurityError"); })).toBe(false);
  expect(await copyDoeEquation("Y = 0", () => ({ writeText: vi.fn().mockRejectedValue(new Error("denied")) }))).toBe(false);
});
