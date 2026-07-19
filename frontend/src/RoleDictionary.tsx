import type { AnalysisMethodDescriptor } from "./api";
import { StatisticalRoleGuide } from "./StatisticalRoleGuide";

export function RoleDictionary({
  selectedMethod = null,
}: {
  selectedMethod?: AnalysisMethodDescriptor | null;
}) {
  return (
    <section aria-labelledby="role-dictionary-title" id="roles">
      <div className="panel-heading help-section-heading">
        <div>
          <h2 id="role-dictionary-title">변수 역할 사전</h2>
          <p>같은 열도 질문에 따라 Response, Predictor, Group, Order 역할이 달라질 수 있습니다.</p>
        </div>
      </div>
      <StatisticalRoleGuide selectedMethod={selectedMethod} />
    </section>
  );
}
