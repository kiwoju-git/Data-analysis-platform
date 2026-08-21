import type { GeneralFactorialDesignCreateRequest } from "./api";

export interface GeneralFactorDraft {
  id: string;
  name: string;
  levelType: "numeric" | "categorical";
  levels: string[];
  unit: string;
  expanded: boolean;
  pasteDraft: string;
}

export interface GeneralFactorialDraftValidation {
  request: GeneralFactorialDesignCreateRequest | null;
  runCount: number;
  message: string | null;
}

export function validateGeneralDraft(
  name: string,
  factors: GeneralFactorDraft[],
  replicatesText: string,
  seedText: string,
  randomize: boolean,
  interactionText: string,
): GeneralFactorialDraftValidation {
  const replicates = Number(replicatesText);
  const seed = Number(seedText);
  const interaction = Number(interactionText);
  const parsed = factors.map((factor) => ({
    ...factor,
    parsedLevels: parseGeneralLevels(factor),
  }));
  const runCount = parsed.reduce(
    (count, factor) => count * factor.levels.length,
    Math.max(1, replicates),
  );
  if (
    !name.trim() ||
    !Number.isInteger(replicates) ||
    replicates < 1 ||
    !Number.isInteger(seed) ||
    seed < 0
  ) {
    return { request: null, runCount, message: "설계 이름, 반복 수와 seed를 확인하세요." };
  }
  if (!Number.isInteger(interaction) || interaction < 1 || interaction > factors.length) {
    return {
      request: null,
      runCount,
      message: "상호작용 차수는 요인 수 이하의 양의 정수여야 합니다.",
    };
  }
  if (
    new Set(parsed.map((factor) => factor.name.trim().toLocaleLowerCase())).size !==
      parsed.length ||
    parsed.some(
      (factor) =>
        !factor.name.trim() || factor.levels.length < 2 || factor.levels.length > 10,
    )
  ) {
    return {
      request: null,
      runCount,
      message: "요인 이름은 고유해야 하며 각 요인은 2~10개 수준이 필요합니다.",
    };
  }
  if (parsed.some((factor) => factor.parsedLevels === null)) {
    return {
      request: null,
      runCount,
      message: "모든 수준을 입력하고 숫자 수준에는 유한한 숫자만 사용하세요.",
    };
  }
  if (parsed.some((factor) => hasDuplicateGeneralLevels(factor))) {
    return {
      request: null,
      runCount,
      message: "한 요인 안에서 수준 값은 중복될 수 없습니다.",
    };
  }
  if (runCount > 256) {
    return { request: null, runCount, message: `예상 ${runCount} runs로 상한 256을 초과합니다.` };
  }
  return {
    request: {
      name: name.trim(),
      factors: parsed.map((factor) => ({
        name: factor.name.trim(),
        levels: factor.parsedLevels ?? [],
        unit: factor.unit.trim() || null,
      })),
      replicates,
      randomize,
      randomization_seed: seed,
      max_interaction_order: interaction,
    },
    runCount,
    message: null,
  };
}

export function parsePastedLevels(value: string): string[] {
  return value
    .split(/[\r\n,]+/u)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function threeLevelPresetLevels(levels: readonly string[]): string[] {
  if (levels.length === 3) return [...levels];
  const first = levels[0] ?? "";
  const last = levels[levels.length - 1] ?? "";
  const middle =
    levels.length > 3 ? (levels[Math.floor((levels.length - 1) / 2)] ?? "") : "";
  return [first, middle, last];
}

function parseGeneralLevels(factor: GeneralFactorDraft): Array<number | string> | null {
  const normalized = factor.levels.map((level) => level.trim());
  if (normalized.some((level) => level === "")) return null;
  if (factor.levelType === "categorical") return normalized;
  const numeric = normalized.map(Number);
  return numeric.every(Number.isFinite) ? numeric : null;
}

function hasDuplicateGeneralLevels(
  factor: GeneralFactorDraft & { parsedLevels: Array<number | string> | null },
): boolean {
  if (factor.parsedLevels === null) return false;
  return (
    new Set(factor.parsedLevels.map((level) => `${typeof level}:${String(level)}`)).size !==
    factor.parsedLevels.length
  );
}
