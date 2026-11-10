import type { AppLocale } from "../../i18n/types";
import { boText } from "./boNoisePolicy";

export function bayesianReviewErrorDetails(code: string, locale: AppLocale) {
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const messages: Record<string, { title: string; message: string; action: string }> = {
    bayesian_vector_goals_invalid: {
      title: text("반응 목표를 확인하세요", "Check the response goals"),
      message: text("반응은 1~4개이며 이름, 유효한 기준값과 양수 중요도가 필요합니다.", "Provide 1–4 named responses, valid thresholds and positive importance weights."),
      action: text("최대화: 하한 < 목표값. 최소화: 목표값 < 상한. 목표값 맞추기: 하한 < 목표값 < 상한. 빈 값은 0이 아닙니다.", "Maximize: lower < target. Minimize: target < upper. Match target: lower < target < upper. Blank values are not zero."),
    },
    bayesian_kernel_invalid: {
      title: text("커널 설정을 확인하세요", "Check the kernel setting"),
      message: text("지원하지 않는 신호 커널입니다.", "The signal kernel is not supported."),
      action: text("목록에서 커널을 선택한 뒤 후보를 다시 검토하세요.", "Choose a kernel from the list and review new candidates."),
    },
    bayesian_review_expired: {
      title: text("후보 검토가 만료되었습니다", "Candidate review expired"),
      message: text("임시 후보가 만료되었거나 서버가 재시작되었습니다.", "The temporary review expired or the server restarted."),
      action: text("현재 관측 이력에서 후보를 다시 생성하세요. 저장된 실험은 삭제되지 않습니다.", "Generate a new review from the current history. Saved experiments are not deleted."),
    },
    bayesian_review_mismatch: {
      title: text("후보 출처가 일치하지 않습니다", "Candidate source mismatch"),
      message: text("Study 또는 후보 설정이 검토한 내용과 일치하지 않습니다.", "The study or candidate configuration differs from the reviewed source."),
      action: text("현재 Study를 새로고침한 뒤 후보를 다시 검토하세요.", "Refresh the current study and review new candidates."),
    },
    bayesian_review_size_exceeded: {
      title: text("후보 검토 크기 제한", "Candidate review size limit"),
      message: text("검토 결과가 허용된 임시 저장 크기를 초과했습니다.", "The review exceeds the temporary storage size limit."),
      action: text("원본 관측은 유지됩니다. 추천 수를 줄인 설정을 명시적으로 선택한 뒤 다시 시도하세요.", "Original observations are unchanged. Explicitly choose a smaller batch and try again."),
    },
    bayesian_review_busy: {
      title: text("다른 후보를 계산 중입니다", "Another review is being calculated"),
      message: text("이 서버에서는 한 번에 하나의 후보 검토를 계산합니다.", "This server calculates one candidate review at a time."),
      action: text("현재 계산이 끝난 뒤 다시 시도하세요.", "Try again after the current calculation finishes."),
    },
    bayesian_recommendation_confirm_failed: {
      title: text("실험 확정 상태를 확인하지 못했습니다", "Experiment confirmation could not be verified"),
      message: text("서버에서 이미 저장되었을 수 있습니다. 검토 후보는 유지됩니다.", "The server may already have saved the experiments. The reviewed candidates are retained."),
      action: text("같은 후보를 다시 확정하거나 Study를 새로고침하여 저장 상태를 확인하세요.", "Confirm the same candidates again or refresh the study to check the saved state."),
    },
  };
  return messages[code] ?? null;
}
