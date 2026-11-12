import { useI18n } from "../../i18n/LocaleProvider";
import { formatMeasurement } from "../../statisticalNumberFormat";
import { boText } from "./boNoisePolicy";

export function BayesianCandidatePurpose({ goal, profile, acquisition, xi, conditionedOn = [] }: {
  goal: string; profile?: string; acquisition: string; xi: number; conditionedOn?: number[];
}) {
  const { locale } = useI18n(), text = (ko: string, en: string) => boText(locale, ko, en);
  const unknown = text("저장 정보 없음", "Not recorded");
  const goals: Record<string, string> = { maximize: text("최대화", "Maximize"), minimize: text("최소화", "Minimize"), match_target: text("목표값 맞추기", "Match target") };
  const profiles: Record<string, string> = { exploitation: text("활용 우선", "Exploitation"), balanced: text("균형", "Balanced"), exploration: text("탐색 우선", "Exploration"), custom: text("직접 설정", "Custom") };
  return <div className="bayesian-candidate-purpose">
    <div>{text("목표", "Goal")}: {goals[goal] ?? unknown}</div>
    {profile && <div>{text("전략", "Strategy")}: {profiles[profile] ?? unknown}</div>}
    <div>{text("선정 기준", "Selection")}: {acquisition === "expected_target_improvement" ? "ETI" : acquisition === "expected_improvement" ? "EI" : unknown}</div>
    <div className="cell-subtext">{conditionedOn.length > 0 ? text("선행 후보에 조건화한 배치 개선", "Batch improvement conditional on earlier candidates") : text("잠재함수의 기대 개선", "Expected latent-function improvement")}</div>
    <div className="cell-subtext">xi = {formatMeasurement(xi, locale)} ({text("표준화 Y", "standardized Y")})</div>
  </div>;
}
