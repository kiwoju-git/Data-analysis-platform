import type { BayesianCurrentBatchResponse, BayesianKernelKind } from "../../api";

export const DEFAULT_BO_KERNEL: BayesianKernelKind = "matern_5_2";

export const BO_KERNEL_OPTIONS: ReadonlyArray<{ kind: BayesianKernelKind; label: string }> = [
  { kind: "matern_5_2", label: "Matérn 5/2" },
  { kind: "matern_3_2", label: "Matérn 3/2" },
  { kind: "gaussian", label: "Gaussian (RBF)" },
  { kind: "exponential", label: "Exponential" },
];

export function parseBoKernelKind(value: unknown): BayesianKernelKind | null {
  return BO_KERNEL_OPTIONS.find(option => option.kind === value)?.kind ?? null;
}

export function savedBoKernelKind(model: BayesianCurrentBatchResponse["shared_model"]): BayesianKernelKind | null {
  return model.schema_version === 3 ? DEFAULT_BO_KERNEL : parseBoKernelKind(model.signal_kernel.family);
}

export function boKernelLabel(kind: BayesianKernelKind | null): string {
  return BO_KERNEL_OPTIONS.find(option => option.kind === kind)?.label ?? "-";
}
