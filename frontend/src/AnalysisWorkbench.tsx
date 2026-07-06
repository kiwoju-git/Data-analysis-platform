import type { ReactNode } from "react";

import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
  AnalysisRunComparisonResponse,
  AnalysisResultExportListResponse,
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
  AnalysisRunListResponse,
  AnalysisRunState,
  DatasetProfileResponse,
  DatasetVersionResponse,
} from "./api";
import { getAnalysisMethodGuidance } from "./analysisMethodGuidance";
import { getAnalysisRunErrorDetails } from "./analysisRunErrors";

interface AnalysisWorkbenchProps {
  catalog: AnalysisMethodListResponse;
  selectedModuleId: AnalysisModuleId;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedAnalysisResult?: AnalysisResultEnvelope | null;
  analysisRunError: string | null;
  analysisResultCsvExport?: AnalysisResultCsvExportResponse | null;
  analysisResultCsvExportError?: string | null;
  analysisResultExportDownloadError?: string | null;
  analysisResultExportList?: AnalysisResultExportListResponse | null;
  analysisResultExportListError?: string | null;
  analysisResultHtmlReport?: AnalysisResultHtmlReportResponse | null;
  analysisResultHtmlReportError?: string | null;
  analysisResultJsonExport?: AnalysisResultJsonExportResponse | null;
  analysisResultJsonExportError?: string | null;
  analysisHistory?: AnalysisRunListResponse | null;
  analysisHistoryError?: string | null;
  analysisHistoryMethodId?: string;
  analysisHistoryOffset?: number;
  analysisHistoryResultAvailabilityFilter?: AnalysisHistoryResultAvailabilityFilter;
  analysisHistoryStaleFilter?: AnalysisHistoryStaleFilter;
  analysisHistoryStatus?: AnalysisRunState | "";
  analysisComparison?: AnalysisRunComparisonResponse | null;
  analysisComparisonError?: string | null;
  analysisComparisonLeftId?: string | null;
  analysisComparisonRightId?: string | null;
  isCreatingAnalysisResultCsvExport?: boolean;
  isCreatingAnalysisResultHtmlReport?: boolean;
  isCreatingAnalysisResultJsonExport?: boolean;
  isDownloadingAnalysisResultExport?: boolean;
  isLoadingAnalysisHistory?: boolean;
  isLoadingAnalysisResultExportList?: boolean;
  isComparingAnalysisRuns?: boolean;
  isRestoringAnalysisResult?: boolean;
  restoredAnalysisResult?: AnalysisResultEnvelope | null;
  restoredAnalysisResultError?: string | null;
  version: DatasetVersionResponse | null;
  profile: DatasetProfileResponse | null;
  onCreateAnalysisResultCsvExport?: (analysisId: string) => void;
  onCreateAnalysisResultHtmlReport?: (analysisId: string) => void;
  onCreateAnalysisResultJsonExport?: (analysisId: string) => void;
  onChangeAnalysisHistoryFilters?: (filters: {
    methodId: string;
    resultAvailability: AnalysisHistoryResultAvailabilityFilter;
    stale: AnalysisHistoryStaleFilter;
    status: AnalysisRunState | "";
  }) => void;
  onChangeAnalysisHistoryPage?: (offset: number) => void;
  onCompareAnalysisRuns?: () => void;
  onDownloadAnalysisResultExport?: (analysisId: string, exportId: string) => void;
  onRefreshAnalysisHistory?: () => void;
  onRestoreAnalysisRun?: (analysisId: string) => void;
  onSelectAnalysisComparisonRun?: (side: "left" | "right", analysisId: string) => void;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  renderAnalysisFilters?: (method: AnalysisMethodDescriptor) => ReactNode;
  renderExecutableMethod: (method: AnalysisMethodDescriptor) => ReactNode;
}

type AnalysisHistoryStaleFilter = "all" | "stale" | "fresh";
type AnalysisHistoryResultAvailabilityFilter = "all" | "available" | "unavailable";

const workbenchSteps = [
  "데이터",
  "역할",
  "옵션",
  "사전점검",
  "실행",
  "결과",
] as const;

const roleGuideItems = [
  {
    title: "Response / 반응값 / Y",
    description: "비교하거나 예측하고 싶은 값입니다. 예: 강도, 수율, 측정값, 온도, 압력",
    risk: "반응값 대신 ID나 그룹 컬럼을 고르면 평균, 효과크기, 회귀계수가 의미 없는 값이 됩니다.",
  },
  {
    title: "Group / 그룹",
    description: "반응값을 나누어 비교할 범주입니다. 예: A라인/B라인, 공급업체, 조건1/조건2",
    risk: "전후 측정인데 group으로 넣으면 독립 2표본 검정이 되어 잘못된 결과가 나올 수 있습니다.",
  },
  {
    title: "Predictor / 설명변수 / X",
    description: "반응값을 설명하거나 예측하는 변수입니다. 예: 온도, 시간, 압력",
    risk: "결과를 만든 뒤에야 알 수 있는 변수를 X로 넣으면 누수 때문에 모델이 과하게 좋아 보입니다.",
  },
  {
    title: "Event level / 사건 수준",
    description: "관심 있는 결과값입니다. 예: Pass, Fail, Defect, Yes",
    risk: "사건 수준을 반대로 고르면 비율, risk ratio, odds ratio 해석이 반대로 바뀝니다.",
  },
  {
    title: "Order / 순서",
    description: "시간 또는 실행 순서입니다. 예: 생산 순서, 측정 순서, timestamp",
    risk: "실제 시간 순서가 아닌 컬럼을 넣으면 추세나 공정 안정성 신호를 잘못 읽을 수 있습니다.",
  },
  {
    title: "Subgroup / 부분군",
    description: "같은 조건에서 묶인 반복 측정 단위입니다. 예: 같은 시간대의 5개 샘플",
    risk: "부분군을 임의로 묶으면 Xbar/R, Xbar/S 관리한계가 공정 구조를 반영하지 못합니다.",
  },
  {
    title: "Part / 부품",
    description: "Gage R&R에서 반복 측정되는 제품 또는 샘플입니다.",
    risk: "부품 ID가 중복되거나 빠지면 반복성/재현성 분산성분을 분리할 수 없습니다.",
  },
  {
    title: "Operator / 측정자",
    description: "Gage R&R에서 측정한 사람 또는 장비입니다.",
    risk: "측정자를 다른 그룹 변수와 혼동하면 재현성 변동을 잘못 추정합니다.",
  },
  {
    title: "Replicate / 반복",
    description: "같은 부품/측정자의 반복 측정 번호입니다.",
    risk: "반복 번호가 균형을 이루지 않으면 현재 balanced crossed Gage R&R은 실행할 수 없습니다.",
  },
  {
    title: "LSL/USL/Target",
    description: "규격 하한, 규격 상한, 목표값입니다.",
    risk: "규격을 관리한계처럼 넣으면 capability 결과를 공정 안정성 판단으로 오해할 수 있습니다.",
  },
] as const;

const purposeGuideItems = [
  {
    question: "한 컬럼의 분포와 이상치를 보고 싶다",
    methods: ["eda.graphical_summary", "eda.descriptive"],
    reason: "분포 모양, 요약 통계, 이상 후보를 먼저 확인합니다.",
    roles: "Response 또는 분석 변수",
  },
  {
    question: "평균이 기준값과 다른지 보고 싶다",
    methods: ["hypothesis.one_sample_t"],
    reason: "한 숫자 컬럼의 평균을 사용자가 정한 기준 평균과 비교합니다.",
    roles: "Response, 기준값",
  },
  {
    question: "두 그룹의 평균을 비교하고 싶다",
    methods: ["hypothesis.two_sample_t"],
    reason: "서로 독립인 두 그룹의 평균 차이를 Welch 기본값으로 봅니다.",
    roles: "Response, Group",
  },
  {
    question: "같은 대상의 전후를 비교하고 싶다",
    methods: ["hypothesis.paired_t"],
    reason: "같은 대상에서 나온 전/후 또는 조건 A/B 차이의 평균을 봅니다.",
    roles: "Before response, After response",
  },
  {
    question: "세 그룹 이상을 비교하고 싶다",
    methods: ["hypothesis.one_way_anova", "hypothesis.kruskal_wallis"],
    reason: "여러 독립 그룹의 차이를 평균 기반 또는 순위 기반으로 비교합니다.",
    roles: "Response, Group",
  },
  {
    question: "두 범주형 변수가 관련 있는지 보고 싶다",
    methods: ["categorical.chi_square_association"],
    reason: "분할표의 기대도수와 카이제곱 통계량으로 관련성을 점검합니다.",
    roles: "Row category, Column category",
  },
  {
    question: "두 숫자 변수가 관련 있는지 보고 싶다",
    methods: ["regression.pearson"],
    reason: "두 연속형 숫자 컬럼의 선형 상관과 신뢰구간을 봅니다.",
    roles: "Predictor X, Response Y",
  },
  {
    question: "공정이 안정적인지 보고 싶다",
    methods: ["quality.individuals_chart", "quality.subgroup_chart", "quality.run_chart"],
    reason: "시간/실행 순서 또는 부분군 구조에서 공정 신호를 확인합니다.",
    roles: "Response, Order 또는 Subgroup",
  },
  {
    question: "규격을 만족하는지 보고 싶다",
    methods: ["quality.capability"],
    reason: "측정값이 LSL/USL/Target 기준으로 얼마나 규격 안에 들어오는지 봅니다.",
    roles: "Response, LSL, USL, Target",
  },
  {
    question: "측정시스템이 믿을 만한지 보고 싶다",
    methods: ["quality.gage_rr"],
    reason: "반복성, 재현성, 부품 간 변동을 balanced crossed 설계에서 분리합니다.",
    roles: "Response, Part, Operator, Replicate",
  },
  {
    question: "실험 조건표를 만들고 싶다",
    methods: ["doe.factorial_design"],
    reason: "2-level full factorial 실행 순서와 재현 가능한 설계표를 만듭니다.",
    roles: "Factor, level, run order",
  },
] as const;

export function AnalysisWorkbench({
  catalog,
  selectedModuleId,
  selectedMethods,
  selectedMethod,
  selectedAnalysisResult = null,
  analysisRunError,
  analysisResultCsvExport = null,
  analysisResultCsvExportError = null,
  analysisResultExportDownloadError = null,
  analysisResultExportList = null,
  analysisResultExportListError = null,
  analysisResultHtmlReport = null,
  analysisResultHtmlReportError = null,
  analysisResultJsonExport = null,
  analysisResultJsonExportError = null,
  analysisHistory = null,
  analysisHistoryError = null,
  analysisHistoryMethodId = "",
  analysisHistoryOffset = 0,
  analysisHistoryResultAvailabilityFilter = "all",
  analysisHistoryStaleFilter = "all",
  analysisHistoryStatus = "",
  analysisComparison = null,
  analysisComparisonError = null,
  analysisComparisonLeftId = null,
  analysisComparisonRightId = null,
  isCreatingAnalysisResultCsvExport = false,
  isCreatingAnalysisResultHtmlReport = false,
  isCreatingAnalysisResultJsonExport = false,
  isDownloadingAnalysisResultExport = false,
  isLoadingAnalysisHistory = false,
  isLoadingAnalysisResultExportList = false,
  isComparingAnalysisRuns = false,
  isRestoringAnalysisResult = false,
  restoredAnalysisResult = null,
  restoredAnalysisResultError = null,
  version,
  profile,
  onCreateAnalysisResultCsvExport = () => undefined,
  onCreateAnalysisResultHtmlReport = () => undefined,
  onCreateAnalysisResultJsonExport = () => undefined,
  onChangeAnalysisHistoryFilters = () => undefined,
  onChangeAnalysisHistoryPage = () => undefined,
  onCompareAnalysisRuns = () => undefined,
  onDownloadAnalysisResultExport = () => undefined,
  onRefreshAnalysisHistory = () => undefined,
  onRestoreAnalysisRun = () => undefined,
  onSelectAnalysisComparisonRun = () => undefined,
  onSelectMethod,
  renderAnalysisFilters,
  renderExecutableMethod,
}: AnalysisWorkbenchProps) {
  const selectedGuidance =
    selectedMethod === null ? null : getAnalysisMethodGuidance(selectedMethod.method_id);
  const executablePanel =
    selectedMethod !== null &&
    (selectedMethod.availability === "available" || selectedMethod.method_id === "quality.gage_rr")
      ? renderExecutableMethod(selectedMethod)
      : null;
  const analysisResultForExport = restoredAnalysisResult ?? selectedAnalysisResult;

  return (
    <>
      <MethodPurposeHelper catalog={catalog} onSelectMethod={onSelectMethod} />
      <StatisticalRoleGuide />
      <nav className="module-nav" aria-label="분석 모듈">
        {catalog.modules.map((module) => (
          <button
            aria-current={module.module_id === selectedModuleId ? "page" : undefined}
            className={
              module.module_id === selectedModuleId
                ? "module-button module-button-active"
                : "module-button"
            }
            key={module.module_id}
            onClick={() => {
              const firstMethod =
                catalog.methods.find((method) => method.module_id === module.module_id) ?? null;
              onSelectMethod(module.module_id, firstMethod?.method_id ?? null);
            }}
            type="button"
          >
            <span>{module.label_ko}</span>
            <small>{module.label_en}</small>
          </button>
        ))}
      </nav>
      <div className="method-grid" aria-label="분석 메서드">
        {selectedMethods.map((method) => (
          <button
            aria-pressed={method.method_id === selectedMethod?.method_id}
            className={
              method.method_id === selectedMethod?.method_id
                ? "method-item method-item-active"
                : "method-item"
            }
            key={method.method_id}
            onClick={() => {
              onSelectMethod(method.module_id, method.method_id);
            }}
            type="button"
          >
            <div className="method-title-row">
              <div>
                <h3>{method.label_ko}</h3>
                <p>{method.label_en}</p>
              </div>
              <span className={`availability-badge availability-${method.availability}`}>
                {availabilityLabel(method)}
              </span>
            </div>
            <div className="method-meta">
              <span>{method.method_id}</span>
              <span>v{method.method_version}</span>
              <span>{method.requires_dataset ? "데이터셋 필요" : "데이터셋 없이 가능"}</span>
            </div>
            {method.disabled_reason !== null ? (
              <p className="method-reason">{method.disabled_reason}</p>
            ) : null}
          </button>
        ))}
      </div>
      {selectedMethod !== null ? (
        <section className="analysis-workbench" aria-labelledby="workbench-title">
          <div className="panel-heading workbench-heading">
            <div>
              <h3 id="workbench-title">{selectedMethod.label_ko}</h3>
              <p>
                {selectedMethod.label_en} · {selectedMethod.method_id}
              </p>
            </div>
            <span className={`availability-badge availability-${selectedMethod.availability}`}>
              {availabilityLabel(selectedMethod)}
            </span>
          </div>
          <ol className="workbench-steps" aria-label="분석 실행 단계">
            {workbenchSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <div className="workbench-summary">
            <div>
              <span>데이터셋</span>
              <strong>
                {version === null
                  ? selectedMethod.requires_dataset
                    ? "필요"
                    : "선택 사항"
                  : `v${version.version_number} · ${version.row_count.toLocaleString()}행`}
              </strong>
            </div>
            <div>
              <span>사전점검</span>
              <strong>
                {profile === null
                  ? "대기"
                  : `${profile.columns.length.toLocaleString()}컬럼 점검됨`}
              </strong>
            </div>
            <div>
              <span>실행 방식</span>
              <strong>{selectedMethod.execution_mode}</strong>
            </div>
          </div>
          <PreflightExplanationPanel
            guidance={selectedGuidance}
            method={selectedMethod}
            profile={profile}
            version={version}
          />
          {renderAnalysisFilters !== undefined ? renderAnalysisFilters(selectedMethod) : null}
          {selectedGuidance !== null ? (
            <>
              {selectedGuidance.plainLanguage !== undefined ||
              selectedGuidance.commonErrors !== undefined ? (
                <section className="method-help-box" aria-label="메서드 쉬운 설명">
                  {selectedGuidance.plainLanguage !== undefined ? (
                    <>
                      <h4>쉽게 말하면</h4>
                      <p>{selectedGuidance.plainLanguage}</p>
                    </>
                  ) : null}
                  {selectedGuidance.commonErrors !== undefined ? (
                    <>
                      <h4>오류가 자주 나는 이유</h4>
                      <ul className="compact-list">
                        {selectedGuidance.commonErrors.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </section>
              ) : null}
              <div className="guidance-grid" aria-label="메서드 입력 계약">
                <section>
                  <h4>필요 역할</h4>
                  <ul className="guidance-list">
                    {selectedGuidance.roleRequirements.map((role) => (
                      <li key={`${role.label}-${role.detail}`}>
                        <strong>{role.label}</strong>
                        <span>{role.required ? "필수" : "선택"}</span>
                        <p>{role.detail}</p>
                      </li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>옵션</h4>
                  <ul className="compact-list">
                    {selectedGuidance.optionChecklist.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>사전점검</h4>
                  <ul className="compact-list">
                    {selectedGuidance.preflightChecks.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>결과 초점</h4>
                  <ul className="compact-list">
                    {selectedGuidance.resultFocus.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
              </div>
            </>
          ) : null}
          {executablePanel !== null && executablePanel !== undefined ? executablePanel : null}
          <AnalysisHistoryPanel
            catalog={catalog}
            history={analysisHistory}
            methodIdFilter={analysisHistoryMethodId}
            offset={analysisHistoryOffset}
            resultAvailabilityFilter={analysisHistoryResultAvailabilityFilter}
            staleFilter={analysisHistoryStaleFilter}
            statusFilter={analysisHistoryStatus}
            isLoading={isLoadingAnalysisHistory}
            isRestoring={isRestoringAnalysisResult}
            restoreError={restoredAnalysisResultError}
            fetchError={analysisHistoryError}
            comparison={analysisComparison}
            comparisonError={analysisComparisonError}
            comparisonLeftId={analysisComparisonLeftId}
            comparisonRightId={analysisComparisonRightId}
            isComparing={isComparingAnalysisRuns}
            restoredResult={restoredAnalysisResult}
            version={version}
            onChangeFilters={onChangeAnalysisHistoryFilters}
            onCompare={onCompareAnalysisRuns}
            onPageChange={onChangeAnalysisHistoryPage}
            onRefresh={onRefreshAnalysisHistory}
            onRestore={onRestoreAnalysisRun}
            onSelectComparisonRun={onSelectAnalysisComparisonRun}
          />
          <AnalysisResultExportPanel
            analysisResult={analysisResultForExport}
            csvExportError={analysisResultCsvExportError}
            csvExportResult={analysisResultCsvExport}
            downloadError={analysisResultExportDownloadError}
            exportList={analysisResultExportList}
            exportListError={analysisResultExportListError}
            htmlReportError={analysisResultHtmlReportError}
            htmlReportResult={analysisResultHtmlReport}
            isExportingCsv={isCreatingAnalysisResultCsvExport}
            isExportingHtml={isCreatingAnalysisResultHtmlReport}
            isExportingJson={isCreatingAnalysisResultJsonExport}
            isDownloadingExport={isDownloadingAnalysisResultExport}
            isLoadingExportList={isLoadingAnalysisResultExportList}
            exportError={analysisResultJsonExportError}
            exportResult={analysisResultJsonExport}
            onCreateCsvExport={onCreateAnalysisResultCsvExport}
            onCreateExport={onCreateAnalysisResultJsonExport}
            onCreateHtmlReport={onCreateAnalysisResultHtmlReport}
            onDownloadExport={onDownloadAnalysisResultExport}
          />
          {analysisRunError !== null ? (
            <AnalysisRunErrorNotice errorCode={analysisRunError} />
          ) : null}
          {executablePanel === null || executablePanel === undefined ? (
            <section className="analysis-run-panel" aria-labelledby="method-status-title">
              <div className="panel-heading">
                <div>
                  <h3 id="method-status-title">실행 상태</h3>
                  <p>{selectedMethod.method_id}</p>
                </div>
                <span className={`availability-badge availability-${selectedMethod.availability}`}>
                  {availabilityLabel(selectedMethod)}
                </span>
              </div>
              <div className="notice-box">{workbenchStatusMessage(selectedMethod)}</div>
            </section>
          ) : null}
        </section>
      ) : null}
    </>
  );
}

function MethodPurposeHelper({
  catalog,
  onSelectMethod,
}: {
  catalog: AnalysisMethodListResponse;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
}) {
  const methodsById = new Map(catalog.methods.map((method) => [method.method_id, method]));

  return (
    <section className="method-purpose-helper" aria-labelledby="method-purpose-helper-title">
      <div className="panel-heading">
        <div>
          <h3 id="method-purpose-helper-title">무엇을 알고 싶나요?</h3>
          <p>질문에서 출발해 후보 method와 필요한 역할을 확인합니다. 선택해도 분석은 자동 실행되지 않습니다.</p>
        </div>
      </div>
      <div className="purpose-card-grid">
        {purposeGuideItems.map((item) => (
          <article className="purpose-card" key={item.question}>
            <h4>{item.question}</h4>
            <p>{item.reason}</p>
            <div className="purpose-role-line">
              <strong>필요 역할</strong>
              <span>{item.roles}</span>
            </div>
            <div className="purpose-method-list">
              {item.methods.map((methodId) => {
                const method = methodsById.get(methodId) ?? null;
                const canSelect = method !== null && method.availability === "available";
                return (
                  <button
                    aria-label={`${methodId} 메서드 보기`}
                    className={
                      canSelect
                        ? "purpose-method-button"
                        : "purpose-method-button purpose-method-button-muted"
                    }
                    disabled={!canSelect}
                    key={methodId}
                    onClick={() => {
                      if (method !== null) {
                        onSelectMethod(method.module_id, method.method_id);
                      }
                    }}
                    type="button"
                  >
                    <code>{methodId}</code>
                    <span>
                      {method === null
                        ? "catalog 없음"
                        : method.availability === "available"
                          ? "메서드 보기"
                          : availabilityLabel(method)}
                    </span>
                  </button>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function StatisticalRoleGuide() {
  return (
    <section className="role-guide-panel" aria-labelledby="role-guide-title">
      <div className="panel-heading">
        <div>
          <h3 id="role-guide-title">역할 설명</h3>
          <p>분석은 column의 통계 역할을 기준으로 실행됩니다. 같은 컬럼이라도 역할 선택이 달라지면 질문과 가정이 달라집니다.</p>
        </div>
      </div>
      <div className="role-guide-grid">
        {roleGuideItems.map((item) => (
          <article className="role-guide-item" key={item.title}>
            <h4>{item.title}</h4>
            <p>{item.description}</p>
            <small>{item.risk}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function PreflightExplanationPanel({
  guidance,
  method,
  profile,
  version,
}: {
  guidance: ReturnType<typeof getAnalysisMethodGuidance> | null;
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

function AnalysisHistoryPanel({
  catalog,
  history,
  methodIdFilter,
  offset,
  resultAvailabilityFilter,
  staleFilter,
  statusFilter,
  isLoading,
  isRestoring,
  fetchError,
  comparison,
  comparisonError,
  comparisonLeftId,
  comparisonRightId,
  isComparing,
  restoreError,
  restoredResult,
  version,
  onChangeFilters,
  onCompare,
  onPageChange,
  onRefresh,
  onRestore,
  onSelectComparisonRun,
}: {
  catalog: AnalysisMethodListResponse;
  history: AnalysisRunListResponse | null;
  methodIdFilter: string;
  offset: number;
  resultAvailabilityFilter: AnalysisHistoryResultAvailabilityFilter;
  staleFilter: AnalysisHistoryStaleFilter;
  statusFilter: AnalysisRunState | "";
  isLoading: boolean;
  isRestoring: boolean;
  fetchError: string | null;
  comparison: AnalysisRunComparisonResponse | null;
  comparisonError: string | null;
  comparisonLeftId: string | null;
  comparisonRightId: string | null;
  isComparing: boolean;
  restoreError: string | null;
  restoredResult: AnalysisResultEnvelope | null;
  version: DatasetVersionResponse | null;
  onChangeFilters: (filters: {
    methodId: string;
    resultAvailability: AnalysisHistoryResultAvailabilityFilter;
    stale: AnalysisHistoryStaleFilter;
    status: AnalysisRunState | "";
  }) => void;
  onCompare: () => void;
  onPageChange: (offset: number) => void;
  onRefresh: () => void;
  onRestore: (analysisId: string) => void;
  onSelectComparisonRun: (side: "left" | "right", analysisId: string) => void;
}) {
  const pageStart = history === null || history.returned_count === 0 ? 0 : history.offset + 1;
  const pageEnd = history === null ? 0 : history.offset + history.returned_count;
  const canMovePrevious = history !== null && history.offset > 0;
  const canMoveNext = history?.has_more === true;

  return (
    <section className="analysis-history-panel" aria-labelledby="analysis-history-title">
      <div className="panel-heading">
        <div>
          <h4 id="analysis-history-title">저장된 분석</h4>
          <p>{version === null ? "데이터셋 확정 후 조회 가능" : `Dataset v${version.version_number}`}</p>
        </div>
        <button
          className="secondary-button compact-button"
          disabled={version === null || isLoading}
          onClick={onRefresh}
          type="button"
        >
          {isLoading ? "조회 중" : "새로고침"}
        </button>
      </div>
      <div className="analysis-history-controls">
        <label>
          <span>method</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: event.currentTarget.value,
                resultAvailability: resultAvailabilityFilter,
                stale: staleFilter,
                status: statusFilter,
              });
            }}
            value={methodIdFilter}
          >
            <option value="">전체</option>
            {catalog.methods.map((method) => (
              <option key={method.method_id} value={method.method_id}>
                {method.method_id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>status</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: resultAvailabilityFilter,
                stale: staleFilter,
                status: event.currentTarget.value as AnalysisRunState | "",
              });
            }}
            value={statusFilter}
          >
            <option value="">전체</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="cancelled">cancelled</option>
            <option value="running">running</option>
            <option value="queued">queued</option>
            <option value="cancel_requested">cancel_requested</option>
          </select>
        </label>
        <label>
          <span>stale</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: resultAvailabilityFilter,
                stale: event.currentTarget.value as AnalysisHistoryStaleFilter,
                status: statusFilter,
              });
            }}
            value={staleFilter}
          >
            <option value="all">전체</option>
            <option value="stale">stale</option>
            <option value="fresh">fresh</option>
          </select>
        </label>
        <label>
          <span>result</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: event.currentTarget
                  .value as AnalysisHistoryResultAvailabilityFilter,
                stale: staleFilter,
                status: statusFilter,
              });
            }}
            value={resultAvailabilityFilter}
          >
            <option value="all">전체</option>
            <option value="available">있음</option>
            <option value="unavailable">없음</option>
          </select>
        </label>
      </div>
      {fetchError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>분석 이력 조회 실패</h4>
          <code>오류 코드: {fetchError}</code>
        </div>
      ) : null}
      {version !== null && history !== null && history.runs.length === 0 ? (
        <div className="notice-box">저장된 분석 결과가 아직 없습니다.</div>
      ) : null}
      {history !== null && history.runs.length > 0 ? (
        <div className="analysis-history-list" aria-label="저장된 분석 목록">
          {history.runs.map((run) => (
            <article className="analysis-history-item" key={run.analysis_id}>
              <div>
                <strong>{run.method_id}</strong>
                <p>
                  v{run.method_version} · {run.status} · {formatDateTime(run.created_at)}
                </p>
                <div className="method-meta">
                  <span>{run.result_available ? "result 있음" : "result 없음"}</span>
                  <span>{run.artifact_count.toLocaleString()} artifacts</span>
                  {run.stale ? <span className="stale-badge">stale</span> : null}
                </div>
              </div>
              <div className="analysis-history-actions">
                <button
                  className="secondary-button compact-button"
                  disabled={!run.result_available || isRestoring}
                  onClick={() => {
                    onRestore(run.analysis_id);
                  }}
                  type="button"
                >
                  {isRestoring ? "불러오는 중" : "결과 불러오기"}
                </button>
                <button
                  className={
                    comparisonLeftId === run.analysis_id
                      ? "secondary-button compact-button selected-compact-button"
                      : "secondary-button compact-button"
                  }
                  disabled={!run.result_available}
                  onClick={() => {
                    onSelectComparisonRun("left", run.analysis_id);
                  }}
                  type="button"
                >
                  왼쪽
                </button>
                <button
                  className={
                    comparisonRightId === run.analysis_id
                      ? "secondary-button compact-button selected-compact-button"
                      : "secondary-button compact-button"
                  }
                  disabled={!run.result_available}
                  onClick={() => {
                    onSelectComparisonRun("right", run.analysis_id);
                  }}
                  type="button"
                >
                  오른쪽
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <div className="analysis-comparison-box" aria-label="저장된 분석 비교">
        <div>
          <strong>비교</strong>
          <span>left {comparisonLeftId === null ? "-" : shortHash(comparisonLeftId)}</span>
          <span>right {comparisonRightId === null ? "-" : shortHash(comparisonRightId)}</span>
        </div>
        <button
          className="secondary-button compact-button"
          disabled={
            comparisonLeftId === null ||
            comparisonRightId === null ||
            comparisonLeftId === comparisonRightId ||
            isComparing
          }
          onClick={onCompare}
          type="button"
        >
          {isComparing ? "비교 중" : "비교"}
        </button>
      </div>
      {comparisonError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>분석 비교 실패</h4>
          <code>오류 코드: {comparisonError}</code>
        </div>
      ) : null}
      {comparison !== null ? <AnalysisComparisonResult comparison={comparison} /> : null}
      {history !== null ? (
        <div className="analysis-history-pagination" aria-label="저장된 분석 페이지">
          <span>
            {pageStart.toLocaleString()}-{pageEnd.toLocaleString()} / page size{" "}
            {history.limit.toLocaleString()}
          </span>
          <div>
            <button
              className="secondary-button compact-button"
              disabled={!canMovePrevious || isLoading}
              onClick={() => {
                onPageChange(Math.max(0, offset - history.limit));
              }}
              type="button"
            >
              이전
            </button>
            <button
              className="secondary-button compact-button"
              disabled={!canMoveNext || isLoading}
              onClick={() => {
                onPageChange(offset + history.limit);
              }}
              type="button"
            >
              다음
            </button>
          </div>
        </div>
      ) : null}
      {restoreError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>저장 결과 불러오기 실패</h4>
          <code>오류 코드: {restoreError}</code>
        </div>
      ) : null}
      {restoredResult !== null ? (
        <div className="restored-result-box" role="status">
          <strong>불러온 결과</strong>
          <span>{restoredResult.method_id}</span>
          <span>{restoredResult.status}</span>
          <span>warning {restoredResult.warnings.length.toLocaleString()}개</span>
          <code>{restoredResult.analysis_id}</code>
          {typeof restoredResult.result?.summary_type === "string" ? (
            <span>{restoredResult.result.summary_type}</span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function AnalysisComparisonResult({ comparison }: { comparison: AnalysisRunComparisonResponse }) {
  return (
    <div className="analysis-comparison-result" role="status">
      <div className="panel-heading">
        <div>
          <h4>비교 결과</h4>
          <p>{comparison.comparable ? "compatible" : "incompatible"}</p>
        </div>
        <span className={comparison.comparable ? "status-pill status-ready" : "status-pill"}>
          {comparison.comparable ? "비교 가능" : "조건 다름"}
        </span>
      </div>
      <div className="comparison-side-grid">
        <ComparisonSide label="left" side={comparison.left} />
        <ComparisonSide label="right" side={comparison.right} />
      </div>
      <div className="comparison-compatibility">
        <span>method {comparison.compatibility.same_method_id ? "same" : "diff"}</span>
        <span>version {comparison.compatibility.same_method_version ? "same" : "diff"}</span>
        <span>dataset {comparison.compatibility.same_dataset_version_id ? "same" : "diff"}</span>
        <span>summary {comparison.compatibility.same_summary_type ? "same" : "diff"}</span>
      </div>
      {comparison.method_specific?.descriptive_statistics !== null &&
      comparison.method_specific?.descriptive_statistics !== undefined ? (
        <DescriptiveComparisonTable comparison={comparison.method_specific.descriptive_statistics} />
      ) : null}
      {comparison.method_specific?.one_sample_t_test !== null &&
      comparison.method_specific?.one_sample_t_test !== undefined ? (
        <OneSampleTComparisonTable comparison={comparison.method_specific.one_sample_t_test} />
      ) : null}
      {comparison.method_specific?.two_sample_t_test !== null &&
      comparison.method_specific?.two_sample_t_test !== undefined ? (
        <TwoSampleTComparisonTable comparison={comparison.method_specific.two_sample_t_test} />
      ) : null}
      {comparison.method_specific?.paired_t_test !== null &&
      comparison.method_specific?.paired_t_test !== undefined ? (
        <PairedTComparisonTable comparison={comparison.method_specific.paired_t_test} />
      ) : null}
      {comparison.method_specific?.equivalence_tost !== null &&
      comparison.method_specific?.equivalence_tost !== undefined ? (
        <EquivalenceTostComparisonTable
          comparison={comparison.method_specific.equivalence_tost}
        />
      ) : null}
      {comparison.method_specific?.one_way_anova !== null &&
      comparison.method_specific?.one_way_anova !== undefined ? (
        <OneWayAnovaComparisonTable comparison={comparison.method_specific.one_way_anova} />
      ) : null}
      {comparison.method_specific?.kruskal_wallis !== null &&
      comparison.method_specific?.kruskal_wallis !== undefined ? (
        <KruskalWallisComparisonTable
          comparison={comparison.method_specific.kruskal_wallis}
        />
      ) : null}
      {comparison.differences.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>field</th>
                <th>left</th>
                <th>right</th>
              </tr>
            </thead>
            <tbody>
              {comparison.differences.map((difference) => (
                <tr key={difference.field}>
                  <td>{difference.field}</td>
                  <td>{comparisonCellValue(difference.left)}</td>
                  <td>{comparisonCellValue(difference.right)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">metadata 차이가 없습니다.</div>
      )}
    </div>
  );
}

function DescriptiveComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["descriptive_statistics"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="기술통계 비교">
      <h4>기술통계 비교</h4>
      {comparison.columns.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>column</th>
                <th>metric</th>
                <th>left</th>
                <th>right</th>
                <th>delta</th>
              </tr>
            </thead>
            <tbody>
              {comparison.columns.flatMap((column) =>
                column.metrics.map((metric) => (
                  <tr key={`${column.column_id}-${metric.metric}`}>
                    <td>{column.display_name}</td>
                    <td>{metric.metric}</td>
                    <td>{comparisonNumberCell(metric.left)}</td>
                    <td>{comparisonNumberCell(metric.right)}</td>
                    <td>{comparisonNumberCell(metric.delta)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">공통 column_id가 없습니다.</div>
      )}
      {comparison.left_only_column_ids.length > 0 ||
      comparison.right_only_column_ids.length > 0 ? (
        <div className="comparison-compatibility">
          <span>left-only {comparison.left_only_column_ids.length.toLocaleString()}</span>
          <span>right-only {comparison.right_only_column_ids.length.toLocaleString()}</span>
        </div>
      ) : null}
    </section>
  );
}

function OneSampleTComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["one_sample_t_test"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="1-표본 t-검정 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>1-표본 t-검정 비교</h4>
          <p>{comparison.response_display_name ?? "response column"}</p>
        </div>
        <span className={comparison.same_response_column ? "status-pill status-ready" : "status-pill"}>
          {comparison.same_response_column ? "같은 response" : "response 다름"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>left {comparison.left_response_column_id ?? "-"}</span>
        <span>right {comparison.right_response_column_id ?? "-"}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TwoSampleTComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["two_sample_t_test"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="2-표본 t-검정 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>2-표본 t-검정 비교</h4>
          <p>
            {comparison.response_display_name ?? "response column"} /{" "}
            {comparison.group_display_name ?? "group column"}
          </p>
        </div>
        <span
          className={
            comparison.same_response_column &&
            comparison.same_group_column &&
            comparison.same_group_label_set
              ? "status-pill status-ready"
              : "status-pill"
          }
        >
          {comparison.same_response_column &&
          comparison.same_group_column &&
          comparison.same_group_label_set
            ? "같은 비교축"
            : "비교축 확인"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>response {comparison.same_response_column ? "same" : "diff"}</span>
        <span>group column {comparison.same_group_column ? "same" : "diff"}</span>
        <span>group set {comparison.same_group_label_set ? "same" : "diff"}</span>
        <span>group order {comparison.same_group_label_order ? "same" : "diff"}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PairedTComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["paired_t_test"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="대응표본 t-검정 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>대응표본 t-검정 비교</h4>
          <p>
            {comparison.before_display_name ?? "before column"} →{" "}
            {comparison.after_display_name ?? "after column"}
          </p>
        </div>
        <span
          className={
            comparison.same_before_column && comparison.same_after_column
              ? "status-pill status-ready"
              : "status-pill"
          }
        >
          {comparison.same_before_column && comparison.same_after_column
            ? "같은 before/after"
            : "before/after 확인"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>before {comparison.same_before_column ? "same" : "diff"}</span>
        <span>after {comparison.same_after_column ? "same" : "diff"}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EquivalenceTostComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["equivalence_tost"];
}) {
  if (comparison === null) {
    return null;
  }
  const equivalentSetting = comparison.settings.find(
    (setting) => setting.setting === "tost.equivalent",
  );
  return (
    <section className="comparison-method-section" aria-label="동등성 TOST 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>동등성 TOST 비교</h4>
          <p>{comparison.response_display_name ?? "response column"}</p>
        </div>
        <span
          className={
            comparison.same_response_column &&
            (equivalentSetting === undefined || equivalentSetting.same)
              ? "status-pill status-ready"
              : "status-pill"
          }
        >
          {comparison.same_response_column ? "같은 response" : "response 다름"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>response {comparison.same_response_column ? "same" : "diff"}</span>
        {equivalentSetting !== undefined ? (
          <span>equivalent decision {equivalentSetting.same ? "same" : "diff"}</span>
        ) : null}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function OneWayAnovaComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["one_way_anova"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="일원분산분석 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>일원분산분석 비교</h4>
          <p>
            {comparison.response_display_name ?? "response column"} /{" "}
            {comparison.group_display_name ?? "group column"}
          </p>
        </div>
        <span
          className={
            comparison.same_response_column &&
            comparison.same_group_column &&
            comparison.same_group_label_set
              ? "status-pill status-ready"
              : "status-pill"
          }
        >
          {comparison.same_response_column &&
          comparison.same_group_column &&
          comparison.same_group_label_set
            ? "같은 비교축"
            : "비교축 확인"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>response {comparison.same_response_column ? "same" : "diff"}</span>
        <span>group column {comparison.same_group_column ? "same" : "diff"}</span>
        <span>group set {comparison.same_group_label_set ? "same" : "diff"}</span>
        <span>group order {comparison.same_group_label_order ? "same" : "diff"}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function KruskalWallisComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["kruskal_wallis"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="Kruskal-Wallis 비교">
      <div className="panel-heading compact-heading">
        <div>
          <h4>Kruskal-Wallis 비교</h4>
          <p>
            {comparison.response_display_name ?? "response column"} /{" "}
            {comparison.group_display_name ?? "group column"}
          </p>
        </div>
        <span
          className={
            comparison.same_response_column &&
            comparison.same_group_column &&
            comparison.same_group_label_set
              ? "status-pill status-ready"
              : "status-pill"
          }
        >
          {comparison.same_response_column &&
          comparison.same_group_column &&
          comparison.same_group_label_set
            ? "같은 비교축"
            : "비교축 확인"}
        </span>
      </div>
      <div className="comparison-compatibility">
        <span>response {comparison.same_response_column ? "same" : "diff"}</span>
        <span>group column {comparison.same_group_column ? "same" : "diff"}</span>
        <span>group set {comparison.same_group_label_set ? "same" : "diff"}</span>
        <span>group order {comparison.same_group_label_order ? "same" : "diff"}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ComparisonSide({
  label,
  side,
}: {
  label: string;
  side: AnalysisRunComparisonResponse["left"];
}) {
  return (
    <div className="comparison-side-card">
      <strong>{label}</strong>
      <span>{side.method_id}</span>
      <span>v{side.method_version}</span>
      <span>{side.summary_type ?? "summary 없음"}</span>
      <span>
        rows {side.row_count_included?.toLocaleString() ?? "-"} /{" "}
        {side.row_count_total?.toLocaleString() ?? "-"}
      </span>
      <span>warnings {side.warning_count.toLocaleString()}</span>
      {side.stale ? <span className="stale-badge">stale</span> : null}
      <code>{shortHash(side.result_sha256)}</code>
    </div>
  );
}

function AnalysisResultExportPanel({
  analysisResult,
  csvExportError,
  csvExportResult,
  downloadError,
  exportError,
  exportList,
  exportListError,
  exportResult,
  htmlReportError,
  htmlReportResult,
  isExportingCsv,
  isExportingHtml,
  isExportingJson,
  isDownloadingExport,
  isLoadingExportList,
  onCreateCsvExport,
  onCreateExport,
  onCreateHtmlReport,
  onDownloadExport,
}: {
  analysisResult: AnalysisResultEnvelope | null;
  csvExportError: string | null;
  csvExportResult: AnalysisResultCsvExportResponse | null;
  downloadError: string | null;
  exportError: string | null;
  exportList: AnalysisResultExportListResponse | null;
  exportListError: string | null;
  exportResult: AnalysisResultJsonExportResponse | null;
  htmlReportError: string | null;
  htmlReportResult: AnalysisResultHtmlReportResponse | null;
  isExportingCsv: boolean;
  isExportingHtml: boolean;
  isExportingJson: boolean;
  isDownloadingExport: boolean;
  isLoadingExportList: boolean;
  onCreateCsvExport: (analysisId: string) => void;
  onCreateExport: (analysisId: string) => void;
  onCreateHtmlReport: (analysisId: string) => void;
  onDownloadExport: (analysisId: string, exportId: string) => void;
}) {
  if (analysisResult === null || analysisResult.status !== "succeeded") {
    return null;
  }

  const matchingExport =
    exportResult !== null && exportResult.analysis_id === analysisResult.analysis_id
      ? exportResult
      : null;
  const matchingCsvExport =
    csvExportResult !== null && csvExportResult.analysis_id === analysisResult.analysis_id
      ? csvExportResult
      : null;
  const matchingHtmlReport =
    htmlReportResult !== null && htmlReportResult.analysis_id === analysisResult.analysis_id
      ? htmlReportResult
      : null;

  return (
    <section className="analysis-export-panel" aria-labelledby="analysis-export-title">
      <div className="panel-heading">
        <div>
          <h4 id="analysis-export-title">결과 내보내기</h4>
          <p>{analysisResult.method_id}</p>
        </div>
        <div className="button-row">
          <button
            className="secondary-button"
            disabled={isExportingJson}
            onClick={() => {
              onCreateExport(analysisResult.analysis_id);
            }}
            type="button"
          >
            {isExportingJson ? "JSON 생성 중" : "JSON 생성"}
          </button>
          <button
            className="secondary-button"
            disabled={isExportingCsv}
            onClick={() => {
              onCreateCsvExport(analysisResult.analysis_id);
            }}
            type="button"
          >
            {isExportingCsv ? "CSV 생성 중" : "CSV 생성"}
          </button>
          <button
            className="secondary-button"
            disabled={isExportingHtml}
            onClick={() => {
              onCreateHtmlReport(analysisResult.analysis_id);
            }}
            type="button"
          >
            {isExportingHtml ? "HTML 생성 중" : "HTML 생성"}
          </button>
        </div>
      </div>
      {matchingExport !== null ? (
        <div className="export-status-box" role="status">
          <strong>생성됨</strong>
          <span>JSON</span>
          <span>{formatBytes(matchingExport.size_bytes)}</span>
          <code>sha256 {shortHash(matchingExport.sha256)}</code>
          {matchingExport.stale ? <span className="stale-badge">stale</span> : null}
          <button
            className="secondary-button compact-button"
            disabled={isDownloadingExport}
            onClick={() => {
              onDownloadExport(analysisResult.analysis_id, matchingExport.export_id);
            }}
            type="button"
          >
            {isDownloadingExport ? "다운로드 중" : "JSON 다운로드"}
          </button>
        </div>
      ) : null}
      {matchingCsvExport !== null ? (
        <div className="export-status-box" role="status">
          <strong>생성됨</strong>
          <span>CSV</span>
          <span>{matchingCsvExport.row_count.toLocaleString()}행</span>
          <span>{formatBytes(matchingCsvExport.size_bytes)}</span>
          <code>sha256 {shortHash(matchingCsvExport.sha256)}</code>
          {matchingCsvExport.stale ? <span className="stale-badge">stale</span> : null}
          <button
            className="secondary-button compact-button"
            disabled={isDownloadingExport}
            onClick={() => {
              onDownloadExport(analysisResult.analysis_id, matchingCsvExport.export_id);
            }}
            type="button"
          >
            {isDownloadingExport ? "다운로드 중" : "CSV 다운로드"}
          </button>
        </div>
      ) : null}
      {matchingHtmlReport !== null ? (
        <div className="export-status-box" role="status">
          <strong>생성됨</strong>
          <span>HTML</span>
          <span>{matchingHtmlReport.section_count.toLocaleString()}개 항목</span>
          <span>{formatBytes(matchingHtmlReport.size_bytes)}</span>
          <code>sha256 {shortHash(matchingHtmlReport.sha256)}</code>
          {matchingHtmlReport.stale ? <span className="stale-badge">stale</span> : null}
          <button
            className="secondary-button compact-button"
            disabled={isDownloadingExport}
            onClick={() => {
              onDownloadExport(analysisResult.analysis_id, matchingHtmlReport.export_id);
            }}
            type="button"
          >
            {isDownloadingExport ? "다운로드 중" : "HTML 다운로드"}
          </button>
        </div>
      ) : null}
      {isLoadingExportList ? <div className="notice-box">export 목록 조회 중</div> : null}
      {exportListError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>export 목록 조회 실패</h4>
          <code>오류 코드: {exportListError}</code>
        </div>
      ) : null}
      {exportList !== null && exportList.analysis_id === analysisResult.analysis_id ? (
        <div className="export-list-box" aria-label="최근 export 목록">
          <strong>최근 export</strong>
          {exportList.exports.length === 0 ? (
            <span>생성된 export 없음</span>
          ) : (
            exportList.exports.map((item) => (
              <div className="export-list-item" key={item.export_id}>
                <span>{exportKindLabel(item.artifact_kind)}</span>
                <code>sha256 {shortHash(item.sha256)}</code>
                <span>{formatDateTime(item.created_at)}</span>
                <button
                  className="secondary-button compact-button"
                  disabled={isDownloadingExport}
                  onClick={() => {
                    onDownloadExport(analysisResult.analysis_id, item.export_id);
                  }}
                  type="button"
                >
                  다운로드
                </button>
              </div>
            ))
          )}
        </div>
      ) : null}
      {exportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>JSON export 실패</h4>
          <code>오류 코드: {exportError}</code>
        </div>
      ) : null}
      {csvExportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>CSV export 실패</h4>
          <code>오류 코드: {csvExportError}</code>
        </div>
      ) : null}
      {htmlReportError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>HTML report 실패</h4>
          <code>오류 코드: {htmlReportError}</code>
        </div>
      ) : null}
      {downloadError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>export 다운로드 실패</h4>
          <code>오류 코드: {downloadError}</code>
        </div>
      ) : null}
    </section>
  );
}

function AnalysisRunErrorNotice({ errorCode }: { errorCode: string }) {
  const details = getAnalysisRunErrorDetails(errorCode);
  return (
    <div className="error-box analysis-error-box" role="alert">
      <h4>{details.title}</h4>
      <p>{details.message}</p>
      <p>
        <strong>해결 방법:</strong> {details.action}
      </p>
      <code>오류 코드: {errorCode}</code>
    </div>
  );
}

function availabilityLabel(method: AnalysisMethodDescriptor): string {
  if (method.availability === "available") {
    return "사용 가능";
  }
  if (method.availability === "disabled") {
    return "비활성";
  }
  return "계획됨";
}

function workbenchStatusMessage(method: AnalysisMethodDescriptor): string {
  if (method.availability === "disabled") {
    return method.disabled_reason ?? "이 메서드는 현재 비활성 상태입니다.";
  }
  if (method.availability === "planned") {
    return (
      method.disabled_reason ??
      "계산 코드, 기준 데이터, 수치 검증 테스트가 준비된 뒤 실행할 수 있습니다."
    );
  }
  return "선택한 메서드는 현재 실행할 수 있습니다.";
}

function shortHash(value: string): string {
  return value.length <= 12 ? value : value.slice(0, 12);
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value.toLocaleString()} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("ko-KR");
}

function comparisonCellValue(value: string | number | boolean | null): string {
  if (value === null) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return value.length > 24 ? shortHash(value) : value;
}

function comparisonNumberCell(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toPrecision(6);
}

function exportKindLabel(kind: string): string {
  if (kind === "analysis_result_json_export") {
    return "JSON";
  }
  if (kind === "analysis_result_csv_export") {
    return "CSV";
  }
  if (kind === "analysis_result_html_report") {
    return "HTML";
  }
  return kind;
}
