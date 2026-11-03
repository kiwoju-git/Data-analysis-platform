export type CapabilitySpecValidation =
  | { kind: "ready" | "empty" }
  | {
      kind: "error";
      code: "invalid_number" | "invalid_limit_order" | "target_outside_limits";
      messageKey:
        | "capability.validation.numeric"
        | "capability.validation.order"
        | "capability.validation.targetOutside";
    };

export function capabilitySpecValidation(lsl: string, usl: string, target: string): CapabilitySpecValidation {
  const parsedLsl = parseOptionalNumber(lsl);
  const parsedUsl = parseOptionalNumber(usl);
  const parsedTarget = parseOptionalNumber(target);
  if (parsedLsl.kind === "error" || parsedUsl.kind === "error" || parsedTarget.kind === "error") {
    return { kind: "error", code: "invalid_number", messageKey: "capability.validation.numeric" };
  }
  if (parsedLsl.value === null && parsedUsl.value === null) return { kind: "empty" };
  if (parsedLsl.value !== null && parsedUsl.value !== null && parsedLsl.value >= parsedUsl.value) {
    return { kind: "error", code: "invalid_limit_order", messageKey: "capability.validation.order" };
  }
  if (parsedTarget.value !== null && (
    (parsedLsl.value !== null && parsedTarget.value < parsedLsl.value) ||
    (parsedUsl.value !== null && parsedTarget.value > parsedUsl.value)
  )) {
    return { kind: "error", code: "target_outside_limits", messageKey: "capability.validation.targetOutside" };
  }
  return { kind: "ready" };
}

function parseOptionalNumber(value: string): { kind: "ok"; value: number | null } | { kind: "error" } {
  const trimmed = value.trim();
  if (trimmed.length === 0) return { kind: "ok", value: null };
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? { kind: "ok", value: parsed } : { kind: "error" };
}
