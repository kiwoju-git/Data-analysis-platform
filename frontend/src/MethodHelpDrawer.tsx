import { useEffect, useRef } from "react";

import type {
  AnalysisMethodDescriptor,
  DatasetProfileResponse,
  DatasetVersionResponse,
} from "./api";
import { getAnalysisMethodGuidance } from "./analysisMethodGuidance";

export function MethodHelpContent({
  method,
  profile = null,
  version = null,
}: {
  method: AnalysisMethodDescriptor;
  profile?: DatasetProfileResponse | null;
  version?: DatasetVersionResponse | null;
}) {
  const guidance = getAnalysisMethodGuidance(method.method_id);
  const requiredRoles = guidance.roleRequirements.filter((role) => role.required);

  return (
    <div className="method-help-content">
      <HelpSection title="쉽게 말하면">
        <p>{guidance.plainLanguage ?? `${method.label_ko}의 입력, 사전점검, 결과 해석 순서를 확인합니다.`}</p>
      </HelpSection>
      <HelpSection title="언제 사용하는가">
        <p>{method.label_ko} 질문과 데이터 구조가 일치할 때 사용합니다. 실행 전에 설계와 독립성 가정을 확인하세요.</p>
      </HelpSection>
      <HelpSection title="필수 역할">
        <ul>
          {requiredRoles.map((role) => (
            <li key={role.label}><strong>{role.label}</strong>: {role.detail}</li>
          ))}
        </ul>
      </HelpSection>
      <HelpSection title="사용하면 안 되는 경우">
        <ul>
          {(guidance.commonErrors ?? ["선택한 역할과 실제 연구 설계가 일치하지 않는 경우"]).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </HelpSection>
      <HelpSection title="옵션 설명">
        <ul>{guidance.optionChecklist.map((item) => <li key={item}>{item}</li>)}</ul>
      </HelpSection>
      <HelpSection title="사전점검과 결과 해석">
        <div className="preflight-help-context">
          <strong>현재 데이터 상태 (구조 수준)</strong>
          <span>
            {version === null
              ? "선택된 데이터셋 버전 없음"
              : `v${version.version_number} · ${version.row_count.toLocaleString()}행 · ${version.column_count.toLocaleString()}열`}
          </span>
          <span>{profile === null ? "profile 확인 전" : "profile 구조 확인 완료"}</span>
          <span>{method.method_id} · v{method.method_version}</span>
        </div>
        <ul>{guidance.preflightChecks.map((item) => <li key={item}>{item}</li>)}</ul>
        <p>
          실제 usable row와 제외 행은 method 사전점검 또는 실행 결과에서 확정됩니다.
          complete-case 처리, 선택 역할, filter와 결측 정책을 실행 결과에서 다시 확인하세요.
        </p>
        <p>
          독립성은 데이터만으로 증명할 수 없습니다. p-value만으로 차이의 크기, 실무 중요성,
          인과관계 또는 공정 안정성을 결론내리지 마세요.
        </p>
        <strong>결과에서 먼저 볼 값</strong>
        <ul>{guidance.resultFocus.map((item) => <li key={item}>{item}</li>)}</ul>
      </HelpSection>
      <div className="notice-box">
        결과 하나만으로 인과관계나 실무적 중요성을 단정하지 마세요. 추정치, 신뢰구간, 효과크기,
        N/제외, 가정과 경고를 함께 확인해야 합니다.
      </div>
      <a className="text-link" href="/help?section=tutorial">한국어 튜토리얼에서 확인</a>
    </div>
  );
}

export function MethodHelpDrawer({
  method,
  open,
  trigger,
  profile,
  version,
  onClose,
}: {
  method: AnalysisMethodDescriptor;
  open: boolean;
  profile?: DatasetProfileResponse | null;
  trigger: HTMLButtonElement | null;
  version?: DatasetVersionResponse | null;
  onClose: () => void;
}) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        trigger?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open, trigger]);

  if (!open) return null;
  return (
    <aside
      aria-labelledby="method-help-drawer-title"
      className="method-help-drawer"
      id="method-help-drawer"
      role="dialog"
    >
      <div className="method-help-drawer-heading">
        <div>
          <span>분석 도움말</span>
          <h3 id="method-help-drawer-title">{method.label_ko}</h3>
          <code>{method.method_id}</code>
        </div>
        <button
          aria-label="분석 도움말 닫기"
          className="secondary-button compact-button"
          onClick={() => {
            onClose();
            trigger?.focus();
          }}
          ref={closeButtonRef}
          type="button"
        >
          닫기
        </button>
      </div>
      <MethodHelpContent method={method} profile={profile} version={version} />
    </aside>
  );
}

function HelpSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="method-help-section"><h4>{title}</h4>{children}</section>;
}
