import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  DatasetVersionResponse,
  GraphPreviewPanel,
  GraphPreviewType,
  ImrChartPreviewPanel,
  RunChartPreviewPanel,
  ScatterPreviewPanel,
} from "./api";
import { AnalysisFilterControls } from "./AnalysisFilterControls";
import { GraphicalSummaryColumnVisuals } from "./GraphicalSummaryColumnVisuals";
import { ComparativeBoxplotChart } from "./charts/ComparativeBoxplotChart";
import { InteractiveIndividualValueChart } from "./charts/InteractiveIndividualValueChart";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
  type ScatterReferenceLine,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";
import {
  graphBuilderDefinition,
  graphBuilderDefinitions,
} from "./graphBuilderRegistry";
import { graphBuilderColumns, useGraphBuilderState } from "./useGraphBuilderState";

interface GraphBuilderPageProps {
  catalog: AnalysisMethodListResponse | null;
  version: DatasetVersionResponse | null;
  onOpenAnalysis: (method: AnalysisMethodDescriptor) => void;
}

export function GraphBuilderPage({
  catalog,
  version,
  onOpenAnalysis,
}: GraphBuilderPageProps) {
  const state = useGraphBuilderState(version);
  const definition = graphBuilderDefinition(state.graphType);
  const roleColumns = graphBuilderColumns(version);
  const openMethod = (methodId: string) => {
    const method = catalog?.methods.find((candidate) => candidate.method_id === methodId);
    if (method !== undefined) onOpenAnalysis(method);
  };

  return (
    <div className="workspace-stack graph-builder-page">
      <header className="page-heading">
        <div>
          <h2 id="graph-builder-title">그래프 작성</h2>
          <p>현재 데이터셋과 필터 조건에서 그래프 유형과 변수를 직접 선택합니다.</p>
        </div>
      </header>
      {version === null ? (
        <div className="empty-state">데이터셋 버전을 먼저 생성하세요.</div>
      ) : (
        <>
          <section className="summary-band" aria-label="그래프 데이터 범위">
            <span>dataset version v{version.version_number.toLocaleString()}</span>
            <strong>
              {version.row_count.toLocaleString()}행 · {version.column_count.toLocaleString()}열
            </strong>
            <span>생성 {formatDate(version.created_at)}</span>
            <span>
              필터 사용 행{" "}
              {state.result === null
                ? "그래프 생성 후 확정"
                : `${state.result.row_count_included.toLocaleString()} / ${state.result.row_count_total.toLocaleString()}`}
            </span>
          </section>
          <section className="surface-section" aria-labelledby="graph-type-title">
            <h3 id="graph-type-title">그래프 유형</h3>
            <div className="graph-type-grid">
              {graphBuilderDefinitions.map((item) => (
                <button
                  aria-pressed={state.graphType === item.graphType}
                  className={
                    state.graphType === item.graphType
                      ? "graph-type-button is-selected"
                      : "graph-type-button"
                  }
                  key={item.graphType}
                  onClick={() => state.setGraphType(item.graphType)}
                  type="button"
                >
                  <strong>{item.label}</strong>
                  <span>{item.description}</span>
                </button>
              ))}
            </div>
          </section>
          <AnalysisFilterControls
            columns={version.columns}
            drafts={state.filterDrafts}
            onChange={state.setFilterDrafts}
          />
          <section className="surface-section" aria-labelledby="graph-roles-title">
            <h3 id="graph-roles-title">변수 선택</h3>
            {state.graphType === "scatter_plot" ? (
              <ScatterRoleControls state={state} />
            ) : (
              <ValueRoleControls maximum={definition.maximumValues} state={state} />
            )}
            {definition.supportsGroup ? (
              <label className="graph-builder-select">
                <span>그룹 변수 (선택 사항)</span>
                <select
                  value={state.groupColumnId ?? ""}
                  onChange={(event) =>
                    state.setGroupColumnId(event.currentTarget.value || null)
                  }
                >
                  <option value="">선택 안 함</option>
                  {roleColumns.group.map((column) => (
                    <option key={column.column_id} value={column.column_id}>
                      {column.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {definition.supportsOrder ? (
              <label className="graph-builder-select">
                <span>공통 순서 컬럼 (선택 사항)</span>
                <select
                  value={state.orderColumnId ?? ""}
                  onChange={(event) =>
                    state.setOrderColumnId(event.currentTarget.value || null)
                  }
                >
                  <option value="">canonical row order</option>
                  {roleColumns.order.map((column) => (
                    <option key={column.column_id} value={column.column_id}>
                      {column.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {state.graphType === "box_plot" && state.groupColumnId === null ? (
              <fieldset className="inline-options">
                <legend>배치 방식</legend>
                <label>
                  <input
                    checked={state.layout === "combined"}
                    name="graph-layout"
                    onChange={() => state.setLayout("combined")}
                    type="radio"
                  />
                  공통 축
                </label>
                <label>
                  <input
                    checked={state.layout === "small_multiples"}
                    name="graph-layout"
                    onChange={() => state.setLayout("small_multiples")}
                    type="radio"
                  />
                  개별 패널
                </label>
              </fieldset>
            ) : null}
            {state.validationError !== null ? (
              <div className="notice-box">{validationMessage(state.validationError)}</div>
            ) : null}
            <button
              className="primary-button"
              disabled={state.isGenerating || state.validationError !== null}
              onClick={() => void state.generate()}
              type="button"
            >
              {state.isGenerating ? "그래프 생성 중" : "그래프 생성"}
            </button>
            {state.error !== null ? (
              <div className="error-box" role="alert">
                {graphErrorMessage(state.error)}
              </div>
            ) : null}
          </section>
          {state.result !== null ? (
            <section className="result-section" aria-labelledby="graph-preview-result-title">
              <div className="section-title-strip">
                <h3 id="graph-preview-result-title">그래프 결과</h3>
              </div>
              <div className="metadata-grid" aria-label="그래프 provenance">
                <span>사용 행</span>
                <strong>{state.result.row_count_included.toLocaleString()}</strong>
                <span>Visualization schema</span>
                <strong>{state.result.visualization_schema_version}</strong>
                <span>필터 hash</span>
                <strong>{state.result.filter_snapshot_sha256.slice(0, 12)}</strong>
                <span>설정 hash</span>
                <strong>{state.result.preview_config_sha256.slice(0, 12)}</strong>
              </div>
              {state.result.warnings.includes("graph_preview_units_missing") ? (
                <div className="notice-box">
                  단위 정보가 없어 공통 축의 해석을 사용자가 확인해야 합니다.
                </div>
              ) : null}
              <GraphPreviewPanels
                graphType={state.graphType}
                layout={state.layout}
                panels={state.result.panels}
              />
              {state.graphType === "qq_plot" ? (
                <p className="interpretation-note">
                  Q-Q Plot은 직선에 가까운지 시각적으로 검토하는 보조 도구이며 정규성
                  통과를 자동 확정하지 않습니다.
                </p>
              ) : null}
              {state.graphType === "scatter_plot" ? (
                <button
                  className="secondary-button"
                  onClick={() => openMethod("regression.pearson")}
                  type="button"
                >
                  Pearson 상관 분석에서 검정하기
                </button>
              ) : null}
              {state.graphType === "imr_chart" ? (
                <button
                  className="secondary-button"
                  onClick={() => openMethod("quality.individuals_chart")}
                  type="button"
                >
                  I-MR 관리도에서 상세 분석 열기
                </button>
              ) : null}
              <p className="interpretation-note">
                이 결과는 미리보기이며 저장 분석 이력, result artifact 또는 export를 만들지
                않습니다.
              </p>
            </section>
          ) : null}
          <AnalysisOnlyGraphLinks onOpenMethod={openMethod} />
        </>
      )}
    </div>
  );
}

type BuilderState = ReturnType<typeof useGraphBuilderState>;

function ValueRoleControls({
  maximum,
  state,
}: {
  maximum: number;
  state: BuilderState;
}) {
  return (
    <fieldset className="column-checklist">
      <legend>표시할 수치 변수 (최대 {maximum})</legend>
      {state.numericColumns.map((column) => (
        <label key={column.column_id}>
          <input
            checked={state.valueColumnIds.includes(column.column_id)}
            onChange={() =>
              state.setValueColumnIds(toggleId(state.valueColumnIds, column.column_id))
            }
            type="checkbox"
          />
          <span>{column.display_name}</span>
          {column.unit ? <small>{column.unit}</small> : null}
        </label>
      ))}
    </fieldset>
  );
}

function ScatterRoleControls({ state }: { state: BuilderState }) {
  return (
    <div className="graph-role-grid">
      <label className="graph-builder-select">
        <span>X 변수</span>
        <select
          value={state.xColumnId ?? ""}
          onChange={(event) => state.setXColumnId(event.currentTarget.value || null)}
        >
          <option value="">선택</option>
          {state.numericColumns.map((column) => (
            <option key={column.column_id} value={column.column_id}>
              {column.display_name}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="column-checklist">
        <legend>Y 변수 (최대 6)</legend>
        {state.numericColumns.map((column) => (
          <label key={column.column_id}>
            <input
              checked={state.yColumnIds.includes(column.column_id)}
              onChange={() =>
                state.setYColumnIds(toggleId(state.yColumnIds, column.column_id))
              }
              type="checkbox"
            />
            {column.display_name}
          </label>
        ))}
      </fieldset>
    </div>
  );
}

export function graphPreviewGridClassName(graphType: GraphPreviewType): string {
  const suffixByType: Record<GraphPreviewType, string> = {
    box_plot: "box-plot",
    individual_value_plot: "individual-value-plot",
    histogram: "histogram",
    qq_plot: "qq-plot",
    ecdf: "ecdf",
    scatter_plot: "scatter-plot",
    run_chart: "run-chart",
    imr_chart: "imr-chart",
  };
  return `graph-preview-grid graph-preview-grid-${suffixByType[graphType]}`;
}

export function graphPreviewPanelClassName(
  kind: GraphPreviewPanel["kind"],
): string {
  return kind === "individual_values" || kind === "imr_chart"
    ? "graph-preview-panel graph-preview-card-full-row"
    : "graph-preview-panel";
}

export function GraphPreviewPanels({
  graphType,
  layout,
  panels,
}: {
  graphType: GraphPreviewType;
  layout: "combined" | "overlay" | "small_multiples";
  panels: GraphPreviewPanel[];
}) {
  const graphical = panels.flatMap((panel) =>
    panel.kind === "graphical_summary" && panel.result !== null ? [panel.result] : [],
  );
  if (graphType === "box_plot" && layout === "combined" && graphical.length > 1) {
    return (
      <div className="graph-preview-combined">
        <ComparativeBoxplotChart chartId="graph-builder-boxplot" columns={graphical} />
      </div>
    );
  }
  return (
    <div className={graphPreviewGridClassName(graphType)}>
      {panels.map((panel) => (
        <GraphPreviewPanelView graphType={graphType} key={panel.panel_id} panel={panel} />
      ))}
    </div>
  );
}

function GraphPreviewPanelView({
  graphType,
  panel,
}: {
  graphType: GraphPreviewType;
  panel: GraphPreviewPanel;
}) {
  if (panel.status === "failed" || panel.result === null) {
    return (
      <article className={graphPreviewPanelClassName(panel.kind)}>
        <h4>{panel.label}</h4>
        <div className="notice-box">{panel.error_code ?? "그래프 계산 불가"}</div>
      </article>
    );
  }
  if (panel.kind === "graphical_summary") {
    const chart =
      graphType === "box_plot"
        ? "boxplot"
        : graphType === "histogram"
          ? "histogram"
          : graphType === "qq_plot"
            ? "qq"
            : "ecdf";
    return (
      <GraphicalSummaryColumnVisuals
        charts={[chart]}
        column={{ ...panel.result, display_name: panel.label }}
        mode="full"
      />
    );
  }
  if (panel.kind === "individual_values") {
    return (
      <article className={graphPreviewPanelClassName(panel.kind)}>
        <h4>{panel.label}</h4>
        <InteractiveIndividualValueChart
          chartId={`graph-builder-${panel.panel_id}`}
          points={panel.result.points}
        />
      </article>
    );
  }
  if (panel.kind === "scatter") {
    return <ScatterPanel panel={panel} />;
  }
  if (panel.kind === "run_chart") {
    return <RunChartPreview panel={panel} />;
  }
  return <ImrChartPreview panel={panel} />;
}

function ScatterPanel({ panel }: { panel: ScatterPreviewPanel }) {
  const result = panel.result;
  if (result === null) return null;
  const points: InteractiveScatterPoint[] = result.points.map((point, index) => ({
    ariaLabel: `${panel.label} 점 ${index + 1}, X ${formatNumber(point.x)}, Y ${formatNumber(point.y)}`,
    className: "interactive-chart-point",
    details: [
      { label: "X", value: formatNumber(point.x) },
      { label: "Y", value: formatNumber(point.y) },
      { label: "그룹", value: point.group ?? "-" },
    ],
    id: `${panel.panel_id}-${index}`,
    title: `${panel.label} 점 ${index + 1}`,
    x: point.x,
    y: point.y,
  }));
  return (
    <article className={graphPreviewPanelClassName(panel.kind)}>
      <h4>{panel.label}</h4>
      <InteractiveScatterChart
        annotations={[`pairwise complete ${points.length.toLocaleString()}점`, "자동 표본추출 없음"]}
        chartId={panel.panel_id}
        description="X와 Y의 pairwise complete 관측값입니다. 인과관계를 의미하지 않습니다."
        emptyLabel="표시할 점이 없습니다."
        formatValue={formatNumber}
        points={points}
        title={panel.label}
        xLabel={result.x_column.display_name}
        xRange={paddedNumericRange(points.map((point) => point.x))}
        yLabel={result.y_column.display_name}
        yRange={paddedNumericRange(points.map((point) => point.y))}
      />
    </article>
  );
}

function RunChartPreview({ panel }: { panel: RunChartPreviewPanel }) {
  const result = panel.result;
  if (result === null) return null;
  return (
    <SequenceChart
      chartId={panel.panel_id}
      label={`${panel.label} Run Chart`}
      points={result.chart.points.map((point) => ({
        position: point.position,
        value: point.value,
        signalCodes: point.signal_codes,
      }))}
      referenceLines={[
        {
          label: `Median ${formatNumber(result.center_line)}`,
          x1: 1,
          x2: Math.max(1, result.chart.point_count),
          y1: result.center_line,
          y2: result.center_line,
        },
      ]}
    />
  );
}

function ImrChartPreview({ panel }: { panel: ImrChartPreviewPanel }) {
  const result = panel.result;
  if (result === null) return null;
  return (
    <article className="graph-preview-panel">
      <h4>{panel.label}</h4>
      <div className="chart-grid">
        <SequenceChart
          chartId={`${panel.panel_id}-i`}
          label={`${panel.label} I chart`}
          points={result.individuals_chart.points.map((point) => ({
            position: point.position,
            value: point.value,
            signalCodes: point.signal_codes,
          }))}
          referenceLines={controlLines(
            result.individuals_chart.lcl,
            result.individuals_chart.center_line,
            result.individuals_chart.ucl,
            result.individuals_chart.point_count,
          )}
        />
        <SequenceChart
          chartId={`${panel.panel_id}-mr`}
          label={`${panel.label} MR chart`}
          points={result.moving_range_chart.points.map((point) => ({
            position: point.position,
            value: point.value,
            signalCodes: point.signal_codes,
          }))}
          referenceLines={controlLines(
            result.moving_range_chart.lcl,
            result.moving_range_chart.center_line,
            result.moving_range_chart.ucl,
            result.moving_range_chart.point_count,
          )}
        />
      </div>
    </article>
  );
}

function SequenceChart({
  chartId,
  label,
  points,
  referenceLines,
}: {
  chartId: string;
  label: string;
  points: Array<{ position: number; value: number; signalCodes: string[] }>;
  referenceLines: ScatterReferenceLine[];
}) {
  const interactivePoints: InteractiveScatterPoint[] = points.map((point, index) => ({
    ariaLabel: `${label} 위치 ${point.position}, 값 ${formatNumber(point.value)}${
      point.signalCodes.length ? `, 신호 ${point.signalCodes.join(", ")}` : ""
    }`,
    className: "interactive-chart-point",
    details: [
      { label: "위치", value: point.position.toLocaleString() },
      { label: "값", value: formatNumber(point.value) },
      { label: "신호", value: point.signalCodes.join(", ") || "없음" },
    ],
    id: `${chartId}-${index}`,
    title: `${label} ${point.position}`,
    warning: point.signalCodes.length > 0,
    x: point.position,
    y: point.value,
  }));
  const yValues = [
    ...points.map((point) => point.value),
    ...referenceLines.flatMap((line) => [line.y1, line.y2]),
  ];
  return (
    <div className="chart-panel">
      <div className="chart-panel-title">{label}</div>
      <InteractiveScatterChart
        annotations={[`표시 ${points.length.toLocaleString()}점`]}
        chartId={chartId}
        connectPoints="line"
        description={`${label}과 기준선`}
        emptyLabel="표시할 점이 없습니다."
        formatValue={formatNumber}
        points={interactivePoints}
        referenceLines={referenceLines}
        title={label}
        xLabel="Order"
        xRange={paddedNumericRange(points.map((point) => point.position))}
        yLabel="Value"
        yRange={paddedNumericRange(yValues)}
      />
    </div>
  );
}

function controlLines(
  lcl: number,
  center: number,
  ucl: number,
  pointCount: number,
): ScatterReferenceLine[] {
  return [
    { label: `LCL ${formatNumber(lcl)}`, x1: 1, x2: pointCount, y1: lcl, y2: lcl },
    { label: `CL ${formatNumber(center)}`, x1: 1, x2: pointCount, y1: center, y2: center },
    { label: `UCL ${formatNumber(ucl)}`, x1: 1, x2: pointCount, y1: ucl, y2: ucl },
  ];
}

function AnalysisOnlyGraphLinks({
  onOpenMethod,
}: {
  onOpenMethod: (methodId: string) => void;
}) {
  return (
    <section className="surface-section" aria-labelledby="analysis-only-graphs-title">
      <h3 id="analysis-only-graphs-title">분석 전용 그래프</h3>
      <div className="analysis-only-links">
        <article>
          <h4>계수형 관리도</h4>
          <p>불량품 수, 결점 수, 표본 크기 또는 검사 기회가 필요합니다.</p>
          <button className="secondary-button" onClick={() => onOpenMethod("quality.attribute_control_chart")} type="button">
            품질 관리에서 열기
          </button>
        </article>
        <article>
          <h4>공정능력 분석</h4>
          <p>LSL/USL과 공정 안정성 검토가 필요합니다.</p>
          <button className="secondary-button" onClick={() => onOpenMethod("quality.capability")} type="button">
            공정능력 분석 열기
          </button>
        </article>
      </div>
    </section>
  );
}

function toggleId(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function validationMessage(code: string): string {
  const messages: Record<string, string> = {
    dataset_version_required: "데이터셋 버전을 먼저 생성하세요.",
    graph_builder_group_requires_one_value:
      "현재는 여러 수치 변수 비교 또는 한 수치 변수의 그룹 비교 중 하나를 선택합니다.",
    graph_builder_scatter_roles_required: "X 변수 한 개와 Y 변수 한 개 이상을 선택하세요.",
    graph_builder_too_many_values: "이 그래프 유형의 최대 변수 수를 초과했습니다.",
    graph_builder_value_required: "수치 변수를 한 개 이상 선택하세요.",
    filter_value_required: "필터 조건 값을 입력하세요.",
  };
  return messages[code] ?? code;
}

function graphErrorMessage(code: string): string {
  const messages: Record<string, string> = {
    graph_preview_unit_mismatch:
      "단위가 다른 변수는 같은 축에서 직접 비교하면 오해할 수 있습니다. 개별 패널을 사용하세요.",
    individual_value_point_limit_exceeded:
      "Individual Value Plot은 현재 최대 2,000개 점을 표시합니다. 필터를 적용하거나 Box Plot/Histogram을 사용하세요.",
    scatter_point_limit_exceeded: "Scatter Plot 점 수가 표시 한도를 초과했습니다. 필터를 적용하세요.",
  };
  return messages[code] ?? code;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 확인 불가" : date.toLocaleString("ko-KR");
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
