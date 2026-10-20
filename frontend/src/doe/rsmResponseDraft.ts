import { parseDoeResponseNumber } from "./doeResponsePaste";

export function parseRsmResponseDraft(
  runOrders: readonly number[],
  draft: Readonly<Record<number, string>>,
): { ok: true; values: { run_order: number; value: number }[] }
  | { ok: false; code: "doe_rsm_response_values_required" | "doe_rsm_response_run_mismatch" } {
  const expected = new Set(runOrders);
  const keys = Object.keys(draft);
  if (!runOrders.length || expected.size !== runOrders.length ||
    runOrders.some((run) => !Number.isSafeInteger(run) || run < 1) ||
    keys.length !== runOrders.length ||
    keys.some((key) => !expected.has(Number(key)) || String(Number(key)) !== key)) {
    return { ok: false, code: "doe_rsm_response_run_mismatch" };
  }
  const values: { run_order: number; value: number }[] = [];
  for (const run of runOrders) {
    const value = parseDoeResponseNumber(draft[run] ?? "");
    if (value === null) return { ok: false, code: "doe_rsm_response_values_required" };
    values.push({ run_order: run, value });
  }
  return { ok: true, values };
}
