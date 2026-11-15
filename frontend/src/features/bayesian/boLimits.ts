export const MAX_BO_TRIALS = 500;
export const MAX_BO_RESPONSES = 6;

// Suggestions are only for a new draft, never for a restored saved request.
export function suggestedBoTrialBudget(trialCount: number, base = 50, hardLimit = MAX_BO_TRIALS): number {
  return Math.min(MAX_BO_TRIALS, hardLimit, Math.max(base, trialCount + 8));
}
