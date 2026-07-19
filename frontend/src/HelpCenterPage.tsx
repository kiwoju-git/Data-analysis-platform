import { useEffect, useMemo, useState } from "react";

import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import { MethodHelpContent } from "./MethodHelpDrawer";
import { MethodPurposeHelper } from "./MethodPurposeHelper";
import { RoleDictionary } from "./RoleDictionary";

function initialMethodId(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("method_id");
}

export function HelpCenterPage({
  catalog,
  onOpenAnalysis,
}: {
  catalog: AnalysisMethodListResponse | null;
  onOpenAnalysis: (method: AnalysisMethodDescriptor) => void;
}) {
  const [query, setQuery] = useState("");
  const [selectedMethodId, setSelectedMethodId] = useState(initialMethodId);
  const filteredMethods = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("ko-KR");
    if (catalog === null) return [];
    return catalog.methods.filter((method) =>
      normalized === "" || [method.label_ko, method.label_en, method.method_id]
        .some((value) => value.toLocaleLowerCase("ko-KR").includes(normalized)),
    );
  }, [catalog, query]);
  const selectedMethod = catalog?.methods.find((method) => method.method_id === selectedMethodId) ?? null;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const section = new URLSearchParams(window.location.search).get("section");
    if (section === "purpose" || section === "roles" || section === "tutorial") {
      document.getElementById(section)?.scrollIntoView({ block: "start" });
    }
  }, []);

  const selectHelpMethod = (method: AnalysisMethodDescriptor) => {
    setSelectedMethodId(method.method_id);
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      params.set("method_id", method.method_id);
      params.delete("section");
      window.history.replaceState(null, "", `/help?${params.toString()}`);
    }
  };

  return (
    <div className="help-center-page">
      <header className="page-heading-band">
        <div>
          <h2>도움말</h2>
          <p>질문에서 분석을 찾고, 변수 역할과 결과 해석 순서를 확인합니다.</p>
        </div>
      </header>
      <section className="help-quick-start" aria-labelledby="help-quick-start-title">
        <h3 id="help-quick-start-title">빠른 시작</h3>
        <ol>
          <li>데이터를 등록하고 parsing을 확정합니다.</li>
          <li>스키마에서 측정수준과 역할을 확인합니다.</li>
          <li>질문에 맞는 method를 선택하고 사전점검을 읽습니다.</li>
          <li>결과의 추정치, 구간, 효과크기, N/제외와 경고를 함께 봅니다.</li>
        </ol>
      </section>
      {catalog !== null ? (
        <MethodPurposeHelper
          catalog={catalog}
          onSelectMethod={(moduleId, methodId) => {
            const method = catalog.methods.find(
              (candidate) => candidate.module_id === moduleId && candidate.method_id === methodId,
            );
            if (method !== undefined) selectHelpMethod(method);
          }}
        />
      ) : <div className="notice-box">분석 method catalog를 불러오는 중입니다.</div>}
      <RoleDictionary selectedMethod={selectedMethod} />
      <section className="help-method-browser" aria-labelledby="help-method-browser-title">
        <div className="panel-heading help-section-heading">
          <div><h2 id="help-method-browser-title">Method별 설명</h2><p>이름이나 stable method ID로 찾습니다.</p></div>
        </div>
        <label className="help-search-field">
          Method 검색
          <input value={query} onChange={(event) => setQuery(event.target.value)} type="search" />
        </label>
        <div className="help-method-list">
          {filteredMethods.map((method) => (
            <button
              aria-pressed={selectedMethodId === method.method_id}
              className={selectedMethodId === method.method_id ? "help-method-row is-selected" : "help-method-row"}
              key={method.method_id}
              onClick={() => selectHelpMethod(method)}
              type="button"
            >
              <strong>{method.label_ko}</strong><span>{method.label_en}</span><code>{method.method_id}</code>
            </button>
          ))}
        </div>
        {selectedMethod !== null ? (
          <div className="help-method-detail">
            <div className="panel-heading"><div><h3>{selectedMethod.label_ko}</h3><p>v{selectedMethod.method_version}</p></div>
              <button className="primary-button" onClick={() => onOpenAnalysis(selectedMethod)} type="button">이 분석 열기</button>
            </div>
            <MethodHelpContent method={selectedMethod} />
          </div>
        ) : null}
      </section>
      <section className="help-reference-band" id="tutorial">
        <h2>결과 해석과 튜토리얼</h2>
        <p>한국어 end-to-end 튜토리얼은 <code>docs/studio_end_to_end_tutorial_ko.md</code>에 있습니다. 숫자는 실제 API 결과 JSON과 자동 동기화됩니다.</p>
        <h3>자주 발생하는 오류</h3>
        <ul><li>role이나 측정수준 불일치</li><li>필터 후 유효 행 부족</li><li>stale source model 또는 schema 불일치</li><li>저장 artifact checksum 불일치</li></ul>
        <h3>Report/export</h3>
        <p>일반 분석의 JSON/CSV/HTML은 리포트 센터에서 생성합니다. Predict, RSM, Optimizer, Bayesian의 전용 HTML 형식은 현재 지원되지 않습니다.</p>
      </section>
    </div>
  );
}
