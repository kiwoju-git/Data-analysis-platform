import type {
  DatasetColumnProfile,
  DatasetColumnRole,
  DatasetMeasurementLevel,
} from "./api";

export const measurementLevelOptions: Array<{ value: DatasetMeasurementLevel; label: string }> = [
  { value: "unknown", label: "미정" },
  { value: "continuous", label: "연속" },
  { value: "count", label: "카운트" },
  { value: "ordinal", label: "순서" },
  { value: "nominal", label: "명목" },
  { value: "binary", label: "이진" },
  { value: "datetime", label: "날짜시간" },
  { value: "id", label: "ID" },
];

export const columnRoleOptions: Array<{ value: DatasetColumnRole; label: string }> = [
  { value: "unspecified", label: "미지정" },
  { value: "id", label: "ID" },
  { value: "feature", label: "특성" },
  { value: "target", label: "대상" },
  { value: "group", label: "그룹" },
  { value: "time", label: "시간" },
  { value: "order", label: "순서" },
  { value: "subgroup_id", label: "부분군" },
  { value: "part_id", label: "부품" },
  { value: "operator_id", label: "측정자" },
  { value: "replicate_id", label: "반복" },
  { value: "sample_size", label: "표본수" },
  { value: "opportunities", label: "기회수" },
  { value: "factor", label: "요인" },
  { value: "response", label: "반응" },
];

export function shortHash(value: string): string {
  return value.slice(0, 12);
}

export function formatNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 1,
    style: "percent",
  }).format(value);
}

export function formatBytes(value: number): string {
  const units = ["bytes", "KB", "MB", "GB"] as const;
  let currentValue = value;
  let unitIndex = 0;
  while (currentValue >= 1024 && unitIndex < units.length - 1) {
    currentValue /= 1024;
    unitIndex += 1;
  }
  return `${new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: unitIndex === 0 ? 0 : 1,
  }).format(currentValue)} ${units[unitIndex]}`;
}

export function formatProfileSummary(column: DatasetColumnProfile): string {
  const summaries: string[] = [];
  if (column.n_numeric > 0) {
    summaries.push(
      `평균 ${formatNumber(column.numeric_mean)} · 범위 ${formatNumber(
        column.numeric_min,
      )}-${formatNumber(column.numeric_max)}`,
    );
  }
  if (column.datetime_profile !== null && column.datetime_profile.n_datetime > 0) {
    summaries.push(formatDateTimeProfile(column.datetime_profile));
  }
  return summaries.length > 0 ? summaries.join(" · ") : "-";
}

export function measurementLevelLabel(value: DatasetMeasurementLevel): string {
  return measurementLevelOptions.find((level) => level.value === value)?.label ?? value;
}

export function roleLabel(value: DatasetColumnRole): string {
  return columnRoleOptions.find((role) => role.value === value)?.label ?? value;
}

export function delimiterLabel(delimiter: string): string {
  if (delimiter === "\t") {
    return "tab";
  }
  if (delimiter === ",") {
    return "comma";
  }
  if (delimiter === ";") {
    return "semicolon";
  }
  if (delimiter === "|") {
    return "pipe";
  }
  return delimiter;
}

function formatDateTimeProfile(profile: DatasetColumnProfile["datetime_profile"]): string {
  if (profile === null || profile.n_datetime === 0) {
    return "-";
  }
  const formatCandidates = profile.format_candidates
    .slice(0, 2)
    .map((candidate) => `${candidate.format} ${candidate.n_matched.toLocaleString()}개`)
    .join(", ");
  const timezoneSummary =
    profile.timezone_aware_count > 0
      ? ` · TZ ${profile.timezone_aware_count.toLocaleString()}개`
      : "";
  const formatSummary = formatCandidates.length > 0 ? ` · ${formatCandidates}` : "";
  return `날짜 ${profile.n_datetime.toLocaleString()}개 · ${profile.datetime_min ?? "?"}-${
    profile.datetime_max ?? "?"
  }${formatSummary}${timezoneSummary}`;
}
