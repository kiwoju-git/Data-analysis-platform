import { describe, expect, it } from "vitest";
import { bayesianRequestId } from "./bayesianRequestId";

describe("BO idempotency request IDs on HTTP LAN", () => {
  it("uses secure random bytes when randomUUID is unavailable", () => {
    const source = { getRandomValues: <T extends ArrayBufferView | null>(array: T): T => {
      (array as Uint8Array).fill(255); return array;
    } };
    expect(bayesianRequestId(source)).toBe("ffffffff-ffff-4fff-bfff-ffffffffffff");
  });
  it("does not substitute weak randomness", () => {
    expect(() => bayesianRequestId({} as Crypto)).toThrow("bayesian_secure_random_unavailable");
  });
});
