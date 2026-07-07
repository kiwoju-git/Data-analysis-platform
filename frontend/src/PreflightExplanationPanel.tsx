import type {
  AnalysisMethodDescriptor,
  DatasetProfileResponse,
  DatasetVersionResponse,
} from "./api";
import type { AnalysisMethodGuidance } from "./analysisMethodGuidance";

export function PreflightExplanationPanel({
  guidance,
  method,
  profile,
  version,
}: {
  guidance: AnalysisMethodGuidance | null;
  method: AnalysisMethodDescriptor;
  profile: DatasetProfileResponse | null;
  version: DatasetVersionResponse | null;
}) {
  const roleLabels =
    guidance === null
      ? []
      : guidance.roleRequirements.map((role) => `${role.label}(${role.required ? "필수" : "선택"})`);

  return (
    <section className="preflight-explanation-panel" aria-labelledby="preflight-explanation-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="preflight-explanation-title">사전점검 해설</h4>
          <p>{method.method_id}</p>
        </div>
      </div>
      <div className="preflight-explanation-grid">
        <div>
          <strong>사용 행 수</strong>
          <span>
            {version === null
              ? "데이터셋 확정 후 실행 시 계산"
              : `${version.row_count.toLocaleString()}행 중 filter와 complete-case 기준으로 계산`}
          </span>
        </div>
        <div>
          <strong>제외 행 수</strong>
          <span>
            {profile === null
              ? "실행 전 profile 또는 method preflight에서 확인"
              : "결측, 비수치 값, 설계 불일치가 있으면 result에 exclusions로 기록"}
          </span>
        </div>
        <div>
          <strong>결측 처리</strong>
          <span>현재 inferential analysis는 명시적 complete-case 처리와 제외 수 표시를 기본으로 합니다.</span>
        </div>
        <div>
          <strong>선택된 역할</strong>
          <span>{roleLabels.length === 0 ? "method별 역할 계약 확인" : roleLabels.join(", ")}</span>
        </div>
        <div>
          <strong>선택된 method</strong>
          <span>
            {method.label_ko} · v{method.method_version}
          </span>
        </div>
        <div>
          <strong>주요 가정</strong>
          <span>독립성은 데이터만으로 자동 검증할 수 없습니다. 실험/측정 설계를 확인해야 합니다.</span>
        </div>
        <div>
          <strong>말할 수 있는 것</strong>
          <span>선택한 method, 역할, filter, 결측 정책에서의 추정값, 신뢰구간, 효과크기, 경고입니다.</span>
        </div>
        <div>
          <strong>말할 수 없는 것</strong>
          <span>p-value만으로 차이의 크기, 실무 중요성, 인과관계, 공정 안정성을 자동 결론내릴 수 없습니다.</span>
        </div>
      </div>
      <p className="preflight-note">
        p-value는 차이가 있는지의 근거이며, 차이가 얼마나 큰지는 effect size와 confidence interval을 함께 봐야 합니다.
      </p>
    </section>
  );
}
