import { useEffect, useState } from "react";

import "./App.css";
import { fetchHealth, type HealthResponse } from "./api";

type HealthState =
  | { kind: "checking" }
  | { kind: "ready"; response: HealthResponse }
  | { kind: "error"; message: string };

const workflowSteps = [
  ["업로드", "CSV, TSV, XLSX 원본을 보존하고 해시와 파싱 옵션을 기록합니다."],
  ["스키마 확인", "측정 수준, 결측 토큰, ID 후보를 사용자가 확정합니다."],
  ["프로파일", "행/열 수, 결측률, 고유값, 범위, 메모리 추정치를 확인합니다."],
  ["분석", "N, 제외 사유, 가정, 효과크기, 신뢰구간을 결과와 함께 남깁니다."],
] as const;

function statusLabel(health: HealthState): string {
  if (health.kind === "ready") {
    return `API ${health.response.status}`;
  }
  if (health.kind === "error") {
    return health.message;
  }
  return "API 확인 중";
}

function statusClassName(health: HealthState): string {
  if (health.kind === "ready") {
    return "status-pill status-ready";
  }
  if (health.kind === "error") {
    return "status-pill status-error";
  }
  return "status-pill";
}

export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "checking" });

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((response) => {
        setHealth({ kind: "ready", response });
      })
      .catch(() => {
        setHealth({
          kind: "error",
          message: "API 연결 필요",
        });
      });

    return () => {
      controller.abort();
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 단계">
        <div className="brand">
          <h1 className="brand-title">DataLab Studio</h1>
          <p className="brand-subtitle">로컬 분석 작업대</p>
        </div>
        <ol className="nav-list">
          <li className="nav-item nav-item-active">프로젝트</li>
          <li className="nav-item">데이터셋</li>
          <li className="nav-item">분석</li>
          <li className="nav-item">리포트</li>
        </ol>
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="topbar-title">Gate A 기반 구성</p>
          <span className={statusClassName(health)} aria-live="polite">
            {statusLabel(health)}
          </span>
        </header>
        <section className="workspace" aria-labelledby="workspace-title">
          <div className="section">
            <h2 id="workspace-title">통계 분석 흐름</h2>
            <p>
              원본 보존, 명시적 스키마 확인, 페이지 기반 미리보기, 재현 가능한 분석 결과를
              순서대로 구축합니다.
            </p>
          </div>
          <div className="workflow-grid" aria-label="작업 흐름">
            {workflowSteps.map(([title, description]) => (
              <div className="workflow-step" key={title}>
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
