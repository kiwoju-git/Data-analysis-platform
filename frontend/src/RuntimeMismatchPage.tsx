import {
  EXPECTED_API_CONTRACT_VERSION,
  FRONTEND_BUILD_COMMIT,
  MINIMUM_METADATA_SCHEMA_VERSION,
} from "./runtimeCompatibility";
import type { RuntimeCompatibilityState } from "./useRuntimeCompatibilityState";

export function RuntimeCompatibilityGate({
  state,
  onRetry,
}: {
  state: RuntimeCompatibilityState;
  onRetry: () => void;
}) {
  if (state.kind === "checking") {
    return (
      <main className="runtime-gate-page" aria-busy="true">
        <h1>DataLab Studio</h1>
        <p role="status">프런트엔드와 백엔드 호환성을 확인하고 있습니다.</p>
      </main>
    );
  }
  if (state.kind === "compatible") return null;
  return (
    <main className="runtime-gate-page" aria-labelledby="runtime-mismatch-title">
      <section className="runtime-mismatch-panel" role="alert">
        <h1 id="runtime-mismatch-title">프런트엔드와 백엔드 버전이 일치하지 않습니다.</h1>
        <p>관리, 삭제, Predict, Response Optimizer와 Bayesian 작업은 안전을 위해 차단했습니다.</p>
        <dl className="runtime-contract-details">
          <div><dt>Frontend build</dt><dd><code>{FRONTEND_BUILD_COMMIT}</code></dd></div>
          <div><dt>Backend build</dt><dd><code>{state.runtime?.build_commit ?? "확인 불가"}</code></dd></div>
          <div><dt>API contract</dt><dd>expected {EXPECTED_API_CONTRACT_VERSION} / actual {state.runtime?.api_contract_version ?? "확인 불가"}</dd></div>
          <div><dt>Metadata schema</dt><dd>minimum {MINIMUM_METADATA_SCHEMA_VERSION} / actual {state.runtime?.metadata_schema_version ?? "확인 불가"}</dd></div>
        </dl>
        {state.result !== null && state.result.missingCapabilities.length > 0 ? (
          <div><strong>누락 capability</strong><ul>{state.result.missingCapabilities.map((item) => <li key={item}><code>{item}</code></li>)}</ul></div>
        ) : null}
        <code>오류 코드: {state.error}</code>
        <ol>
          <li>이전에 실행한 DataLab PowerShell 창을 모두 종료합니다.</li>
          <li>포트 8000과 5173 listener를 확인합니다.</li>
          <li>최신 폴더에서 <code>bootstrap.ps1</code>을 실행합니다.</li>
          <li>같은 폴더에서 <code>dev.ps1</code>을 실행합니다.</li>
          <li>실행 로그에 표시된 새 브라우저 주소를 열고 Ctrl+F5를 누릅니다.</li>
        </ol>
        <button className="primary-button" onClick={onRetry} type="button">다시 확인</button>
      </section>
    </main>
  );
}
