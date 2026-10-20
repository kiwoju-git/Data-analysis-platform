import { expect, it } from "vitest";
import { ccdBoundsPreview, recommendedCenterPoints, strictRsmInteger } from "./rsmDesignDraft";

it("rejects partial or fractional integers instead of parseInt truncation", () => {
  for (const value of ["5.5", "5abc", "", "NaN", "Infinity", "5e0"]) expect(strictRsmInteger(value)).toBeNull();
  expect(strictRsmInteger(" 0 ")).toBe(0);
  expect(strictRsmInteger("7")).toBe(7);
});
it("previews CCC cube versus axial bounds and scoped center defaults", () => {
  expect(ccdBoundsPreview(10, 20, 4, "circumscribed")).toMatchObject({ center: 15, factorialLow: 10, factorialHigh: 20, axialLow: 5, axialHigh: 25 });
  expect(ccdBoundsPreview(10, 20, 4, "inscribed")).toMatchObject({ center: 15, factorialLow: 12.5, factorialHigh: 17.5, axialLow: 10, axialHigh: 20 });
  expect(ccdBoundsPreview(10, 20, 4, "face_centered")).toMatchObject({ alpha: 1, axialLow: 10, axialHigh: 20 });
  expect([2, 3, 4, 5].map(recommendedCenterPoints)).toEqual([5, 6, 7, 10]);
});
