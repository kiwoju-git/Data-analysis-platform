import type { DatasetProfileResponse } from "./api";
import {
  formatBytes,
  formatPercent,
  formatProfileSummary,
  measurementLevelLabel,
  roleLabel,
  shortHash,
} from "./datasetDisplay";

interface DatasetProfileSectionProps {
  isLoadingProfile: boolean;
  profile: DatasetProfileResponse | null;
  versionId: string;
  onLoadDatasetProfile: (versionId: string) => void;
}

export function DatasetProfileSection({
  isLoadingProfile,
  profile,
  versionId,
  onLoadDatasetProfile,
}: DatasetProfileSectionProps) {
  return (
    <>
      <div className="schema-actions">
        <span>프로파일 / 사전점검</span>
        <button
          className="secondary-button"
          disabled={isLoadingProfile}
          onClick={() => {
            onLoadDatasetProfile(versionId);
          }}
          type="button"
        >
          {isLoadingProfile ? "계산 중" : "다시 계산"}
        </button>
      </div>
      {profile?.warnings.length ? (
        <ul className="warning-list" aria-label="데이터셋 프로파일 경고">
          {profile.warnings.map((warning) => (
            <li key={warning.code}>{warning.message}</li>
          ))}
        </ul>
      ) : null}
      {profile !== null ? (
        <div className="metadata-grid" aria-label="프로파일 사전점검">
          <span>Canonical artifact</span>
          <strong className="hash-text">
            {profile.canonical_artifact === null
              ? "없음"
              : `${shortHash(profile.canonical_artifact.sha256)} · ${formatBytes(
                  profile.canonical_artifact.size_bytes,
                )}`}
          </strong>
          <span>Profile artifact</span>
          <strong className="hash-text">
            {profile.profile_artifact === null
              ? "없음"
              : `${shortHash(profile.profile_artifact.sha256)} · ${formatBytes(
                  profile.profile_artifact.size_bytes,
                )}`}
          </strong>
          <span>메모리 추정</span>
          <strong>{formatBytes(profile.preflight.estimated_memory_bytes)}</strong>
          <span>중복 행</span>
          <strong>
            {profile.preflight.duplicate_row_count.toLocaleString()}
            {profile.preflight.duplicate_row_count_capped ? "+" : ""}
          </strong>
        </div>
      ) : null}
      {profile !== null ? (
        <div className="table-wrap">
          <table className="profile-table">
            <thead>
              <tr>
                <th>컬럼</th>
                <th>역할</th>
                <th>결측</th>
                <th>고유값</th>
                <th>요약</th>
                <th>점검</th>
              </tr>
            </thead>
            <tbody>
              {profile.columns.map((column) => (
                <tr key={column.column_id}>
                  <td>
                    <strong>{column.display_name}</strong>
                    <span className="cell-subtle">{column.data_type}</span>
                  </td>
                  <td>
                    {roleLabel(column.role)}
                    <span className="cell-subtle">
                      {measurementLevelLabel(column.measurement_level)}
                    </span>
                  </td>
                  <td>
                    {column.n_missing.toLocaleString()} / {column.n_total.toLocaleString()}
                    <span className="cell-subtle">{formatPercent(column.missing_rate)}</span>
                  </td>
                  <td>
                    {column.unique_count_capped
                      ? `${profile.unique_count_limit}+`
                      : column.unique_count.toLocaleString()}
                  </td>
                  <td>{formatProfileSummary(column)}</td>
                  <td>
                    {column.warnings.length > 0 ? (
                      <ul className="inline-warning-list">
                        {column.warnings.map((warning) => (
                          <li key={warning.code}>{warning.message}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="cell-subtle">경고 없음</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">
          {isLoadingProfile ? "프로파일 계산 중" : "프로파일을 아직 불러오지 않았습니다."}
        </div>
      )}
    </>
  );
}
