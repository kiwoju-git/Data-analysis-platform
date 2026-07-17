export interface AnalysisRunErrorDetails {
  title: string;
  message: string;
  action: string;
}

const exactErrorDetails: Record<string, AnalysisRunErrorDetails> = {
  analysis_run_failed: {
    title: "분석 실행 실패",
    message: "서버가 분석 요청을 처리하지 못했습니다.",
    action: "입력 역할과 옵션을 다시 확인한 뒤, 같은 오류가 반복되면 오류 코드를 알려주세요.",
  },
  api_unreachable: {
    title: "API 연결 실패",
    message: "브라우저가 로컬 API 서버에 연결하지 못했습니다.",
    action: "프론트와 백엔드 포트가 맞는지 확인하고 페이지를 새로고침하세요.",
  },
  attribute_control_chart_limit_set_method_version_mismatch: {
    title: "Limit set 버전 불일치",
    message: "선택한 limit set을 현재 Phase II 관리도 버전에서 사용할 수 없습니다.",
    action: "현재 앱 버전에서 생성한 호환 limit set을 선택하세요.",
  },
  attribute_control_chart_limit_set_chart_type_mismatch: {
    title: "관리도 유형 불일치",
    message: "선택한 limit set과 관리도 유형이 다릅니다.",
    action: "P, NP, C, U 유형이 같은 limit set을 선택하세요.",
  },
  attribute_control_chart_limit_set_count_definition_mismatch: {
    title: "계수 정의 불일치",
    message: "선택한 limit set과 불량품/결점 정의가 다릅니다.",
    action: "기준선과 같은 계수 정의를 사용하세요.",
  },
  attribute_control_chart_phase_2_target_schema_mismatch: {
    title: "대상 스키마 불일치",
    message: "대상 계수·분모 열의 측정수준, 역할 또는 단위가 기준선과 호환되지 않습니다.",
    action: "기준선과 의미가 같은 숫자 열을 선택하거나 대상 스키마를 확인하세요.",
  },
  attribute_control_chart_phase_2_np_sample_size_mismatch: {
    title: "NP 표본 크기 불일치",
    message: "NP Phase II의 모든 표본 크기는 기준선의 고정 표본 크기와 같아야 합니다.",
    action: "표본 크기를 확인하거나 가변 표본 크기라면 P 관리도를 사용하세요.",
  },
  attribute_control_chart_phase_2_c_opportunity_confirmation_required: {
    title: "검사 기회 확인 필요",
    message: "C Phase II를 실행하려면 현재 검사 기회가 기준선과 동일함을 확인해야 합니다.",
    action: "검사 기회가 실제로 동일한지 검토한 뒤 확인란을 선택하세요.",
  },
  attribute_control_chart_phase_2_dependency_mismatch: {
    title: "Phase II 의존성 검증 실패",
    message: "저장 결과, 대상 데이터 또는 limit set의 관계가 생성 당시와 일치하지 않습니다.",
    action: "변경되지 않은 원본 자산을 복원하거나 검증된 limit set으로 다시 실행하세요.",
  },
  attribute_control_chart_phase_2_no_usable_points: {
    title: "Phase II 유효 관측 없음",
    message: "필터와 complete-case 제외 후 평가할 모니터링 관측이 없습니다.",
    action: "필터, 계수 값, 표본 크기 또는 검사 기회 값을 확인한 뒤 다시 실행하세요.",
  },
  bayesian_study_initial_design_too_small: {
    title: "초기 trial 수 부족",
    message: "Bayesian 추천에 필요한 최소 관측 수보다 초기 trial 수가 적습니다.",
    action: "현재 요인 수 옆에 표시된 최소 trial 수 이상으로 늘린 뒤 study를 생성하세요.",
  },
  bayesian_trial_abandon_would_strand_study: {
    title: "초기 trial 중단 불가",
    message: "이 trial을 중단하면 추천에 필요한 최소 완료 관측 수를 채울 수 없습니다.",
    action: "남은 초기 trial을 먼저 완료하세요. 이 버전에서는 대체 초기 trial을 만들지 않습니다.",
  },
  bayesian_optimization_trial_budget_invalid: {
    title: "전체 trial 예산 오류",
    message: "전체 trial 예산은 2~200 사이의 정수여야 합니다.",
    action: "현재 trial 수보다 큰 예산을 입력하고 다시 추천하세요.",
  },
  bayesian_optimization_budget_exhausted: {
    title: "Bayesian 예산 도달",
    message: "전체 trial 수, 계산 시간, 또는 계산 평가 예산에 도달했습니다.",
    action: "화면의 trial 예산과 저장된 종료 사유를 확인하세요. 오류를 surrogate 적합 실패로 해석하지 마세요.",
  },
  bayesian_observation_invalid: {
    title: "관측값 오류",
    message: "저장할 objective 관측값은 유한한 숫자여야 합니다.",
    action: "실제 실험에서 얻은 값을 확인한 뒤 숫자로 입력하세요.",
  },
  bayesian_study_close_pending_trials: {
    title: "Pending trial 정리 필요",
    message: "Study를 종료하기 전에 모든 pending trial을 완료하거나 명시적으로 중단해야 합니다.",
    action: "trial 표에서 남은 항목을 처리한 뒤 종료를 다시 확인하세요.",
  },
  bayesian_study_completion_requirements_not_met: {
    title: "Study 완료 조건 미충족",
    message: "완료 종료에는 최소 관측 수와 하나 이상의 저장된 recommendation이 필요합니다.",
    action: "필요한 관측과 확인 실험을 기록하거나, 중단 종료가 맞는지 검토하세요.",
  },
  bayesian_study_close_conflict: {
    title: "Study 종료 상태 변경됨",
    message: "화면에 표시된 version 또는 관측 history 이후 study 상태가 변경되었습니다.",
    action: "Study를 다시 불러와 최신 상태와 종료 기록을 확인하세요.",
  },
  bayesian_study_closed: {
    title: "종료된 Study",
    message: "종료된 Bayesian study에는 관측, trial 중단 또는 추천을 추가할 수 없습니다.",
    action: "기존 기록은 읽기 전용으로 확인하고, 계속하려면 successor study를 만드세요.",
  },
  bayesian_study_deletion_active: {
    title: "활성 Study 삭제 불가",
    message: "Bayesian study는 완료 또는 중단으로 종료한 뒤에만 삭제할 수 있습니다.",
    action: "Pending trial을 정리하고 Study 종료 절차를 먼저 완료하세요.",
  },
  bayesian_study_deletion_referenced: {
    title: "참조 중인 Study 삭제 불가",
    message: "Successor study가 이 predecessor study를 참조하고 있어 삭제할 수 없습니다.",
    action: "참조 관계를 보존하세요. 현재 버전은 cascade 삭제를 지원하지 않습니다.",
  },
  bayesian_study_deletion_confirmation_mismatch: {
    title: "삭제 영향이 변경됨",
    message: "삭제 확인 이후 Study graph 또는 확인 대상이 변경되었습니다.",
    action: "삭제 영향 확인을 다시 실행한 뒤 최신 metadata 수와 상태를 검토하세요.",
  },
  bayesian_study_deletion_conflict: {
    title: "Study 삭제 충돌",
    message: "삭제 transaction을 시작하기 전에 Study graph가 변경되었습니다.",
    action: "Study를 다시 불러오고 삭제 영향 확인부터 다시 진행하세요.",
  },
  bayesian_study_predecessor_invalid: {
    title: "Predecessor Study 오류",
    message: "종료가 검증된 Bayesian study만 successor의 predecessor로 사용할 수 있습니다.",
    action: "원 study의 종료 기록을 확인한 뒤 successor 생성을 다시 시도하세요.",
  },
  dataset_version_required: {
    title: "데이터셋 버전 필요",
    message: "분석은 업로드 직후 raw 파일이 아니라 파싱 확정된 dataset version에서 실행됩니다.",
    action: "데이터셋 화면에서 파싱 확정을 완료한 뒤 다시 실행하세요.",
  },
  filter_column_not_found: {
    title: "필터 컬럼 없음",
    message: "분석 필터가 현재 데이터셋 스키마에 없는 컬럼을 가리킵니다.",
    action: "필터를 지우거나 현재 스키마에 있는 컬럼으로 다시 선택하세요.",
  },
  filter_operator_not_supported_for_column: {
    title: "필터 연산자 불일치",
    message: "선택한 컬럼 타입에서 사용할 수 없는 필터 조건입니다.",
    action: "문자 컬럼은 결측, 같음, 다름 조건을 쓰고, 숫자 비교는 수치 컬럼에서만 쓰세요.",
  },
  filter_value_required: {
    title: "필터 값 필요",
    message: "선택한 필터 조건은 비교할 값이 필요합니다.",
    action: "필터 값 입력칸을 채우거나 값이 필요 없는 결측 조건으로 바꾸세요.",
  },
  invalid_equivalence_tost_reference_mean: {
    title: "기준 평균 오류",
    message: "동등성 검정의 기준 평균은 비어 있지 않은 숫자여야 합니다.",
    action: "비교하려는 기준 평균을 숫자로 입력하세요. 예: 10",
  },
  invalid_equivalence_tost_bounds: {
    title: "동등성 한계 오류",
    message: "동등성 하한과 상한은 둘 다 숫자여야 합니다.",
    action: "평균 차이 기준으로 허용 가능한 하한과 상한을 입력하세요. 예: -0.8, 0.8",
  },
  equivalence_tost_bounds_order_invalid: {
    title: "동등성 한계 순서 오류",
    message: "동등성 하한은 상한보다 작아야 합니다.",
    action: "하한/상한 입력칸이 서로 뒤바뀌지 않았는지 확인하세요.",
  },
  invalid_equivalence_tost_alpha: {
    title: "유의수준 alpha 오류",
    message: "TOST의 alpha는 0보다 크고 0.5보다 작아야 합니다.",
    action: "일반적인 시작값은 0.05입니다.",
  },
  equivalence_tost_n_too_small: {
    title: "사용 가능한 데이터 부족",
    message: "동등성 검정을 계산하려면 숫자로 사용할 수 있는 값이 최소 2개 필요합니다.",
    action: "반응 변수가 숫자 컬럼인지 확인하고, 필터가 모든 행을 제외하지 않았는지 확인하세요.",
  },
  equivalence_tost_standard_error_zero: {
    title: "분산이 없어 계산 불가",
    message: "사용된 값이 모두 같으면 표준오차가 0이어서 TOST 통계량을 계산할 수 없습니다.",
    action: "상수 컬럼이 아닌 반응 변수를 선택하거나 필터 조건을 완화하세요.",
  },
  pearson_same_x_and_y_column: {
    title: "같은 컬럼 중복 선택",
    message: "Pearson 상관은 서로 다른 두 수치 컬럼의 관계를 봅니다.",
    action: "X 변수와 Y 변수에 서로 다른 숫자 컬럼을 선택하세요.",
  },
  pearson_n_too_small: {
    title: "사용 가능한 쌍 부족",
    message: "Pearson 상관과 Fisher z 신뢰구간을 계산하려면 complete-case 수치 쌍이 최소 4개 필요합니다.",
    action: "필터를 완화하거나 결측/문자 값이 적은 두 숫자 컬럼을 선택하세요.",
  },
  pearson_x_constant: {
    title: "X 값 변동 없음",
    message: "X 컬럼의 사용 값이 모두 같으면 상관계수를 계산할 수 없습니다.",
    action: "값이 변하는 수치 컬럼을 X 변수로 선택하세요.",
  },
  pearson_y_constant: {
    title: "Y 값 변동 없음",
    message: "Y 컬럼의 사용 값이 모두 같으면 상관계수를 계산할 수 없습니다.",
    action: "값이 변하는 수치 컬럼을 Y 변수로 선택하세요.",
  },
  invalid_descriptive_options: {
    title: "기술통계 옵션 형식 오류",
    message: "기술통계 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "분석할 숫자 컬럼 목록과 결측 처리 옵션을 다시 확인하세요.",
  },
  invalid_pearson_options: {
    title: "Pearson 상관 옵션 형식 오류",
    message: "Pearson 상관 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "X 컬럼, Y 컬럼, alpha, 신뢰수준, 결측 처리 옵션을 다시 확인하세요.",
  },
  invalid_xy_correlation_options: {
    title: "X-Y 상관행렬 옵션 형식 오류",
    message: "X-Y 상관행렬 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "X 컬럼 목록, Y 컬럼 목록, alpha, 신뢰수준, 결측 처리 옵션을 다시 확인하세요.",
  },
  invalid_one_sample_t_options: {
    title: "1-표본 t 옵션 형식 오류",
    message: "1-표본 t-검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, alpha, 신뢰수준, 기준 평균, 대립가설 선택을 다시 확인하세요.",
  },
  invalid_paired_t_options: {
    title: "대응표본 t 옵션 형식 오류",
    message: "대응표본 t-검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "before/after 컬럼, alpha, 신뢰수준, 기준 차이, 대립가설 선택을 다시 확인하세요.",
  },
  invalid_two_sample_t_options: {
    title: "2-표본 t 옵션 형식 오류",
    message: "2-표본 t-검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, alpha, 신뢰수준, 분산 가정, 기준 차이를 다시 확인하세요.",
  },
  invalid_one_sample_wilcoxon_options: {
    title: "Wilcoxon 옵션 형식 오류",
    message: "1-표본 Wilcoxon 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, alpha, 기준 위치, p-value 계산 방식, zero difference 처리 방식을 다시 확인하세요.",
  },
  invalid_mann_whitney_options: {
    title: "Mann-Whitney 옵션 형식 오류",
    message: "Mann-Whitney U 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, alpha, 대립가설, p-value 계산 방식을 다시 확인하세요.",
  },
  invalid_graphical_summary_options: {
    title: "그래프 요약 옵션 형식 오류",
    message: "그래프 요약 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "분석할 숫자 컬럼, 히스토그램 bin 수, Q-Q/ECDF 점 제한 값을 다시 확인하세요.",
  },
  invalid_normality_options: {
    title: "정규성 검정 옵션 형식 오류",
    message: "정규성 검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "분석할 숫자 컬럼, alpha, Q-Q 점 포함 여부와 점 제한 값을 다시 확인하세요.",
  },
  invalid_equal_variances_options: {
    title: "등분산 검정 옵션 형식 오류",
    message: "등분산 검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, alpha, 결측 처리 옵션을 다시 확인하세요.",
  },
  two_sample_t_requires_exactly_two_groups: {
    title: "2개 그룹 필요",
    message:
      "2-표본 t-검정은 필터와 결측 제외 후 사용 가능한 그룹이 정확히 2개여야 합니다.",
    action:
      "그룹 컬럼에 실제로 두 수준만 있는지 확인하고, 필터가 한 그룹을 모두 제외하지 않았는지 확인하세요.",
  },
  two_sample_t_group_n_too_small: {
    title: "그룹별 표본 부족",
    message: "2-표본 t-검정은 두 그룹 모두에서 사용할 수 있는 수치 행이 필요합니다.",
    action: "반응/그룹 컬럼과 필터 조건을 확인해 각 그룹의 사용 가능한 행 수를 늘리세요.",
  },
  two_sample_t_standard_error_zero: {
    title: "표준오차 0",
    message: "선택한 두 그룹의 변동이 없어 t 통계량을 계산할 수 없습니다.",
    action: "상수값만 남지 않도록 반응 컬럼이나 필터 조건을 다시 확인하세요.",
  },
  invalid_one_way_anova_options: {
    title: "ANOVA 옵션 형식 오류",
    message: "일원분산분석 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, alpha, 신뢰수준, ANOVA/사후검정 옵션을 다시 확인하세요.",
  },
  invalid_kruskal_wallis_options: {
    title: "Kruskal-Wallis 옵션 형식 오류",
    message: "Kruskal-Wallis 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, alpha, Dunn/Holm 사후검정 옵션을 다시 확인하세요.",
  },
  invalid_two_proportion_options: {
    title: "2-비율 옵션 형식 오류",
    message: "2-비율 검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 그룹 컬럼, 사건 수준, alpha, 신뢰수준, 대립가설 선택을 다시 확인하세요.",
  },
  invalid_chi_square_options: {
    title: "카이제곱 옵션 형식 오류",
    message: "카이제곱 독립성 검정 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "행 변수, 열 변수, alpha 설정을 다시 확인하세요.",
  },
  invalid_one_proportion_options: {
    title: "1-비율 옵션 형식 오류",
    message: "1-비율 검정 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 컬럼, 사건 수준, 기준 비율, alpha, 신뢰수준, 신뢰구간 방식을 다시 확인하세요.",
  },
  xy_correlation_columns_required: {
    title: "X/Y 변수 필요",
    message: "X-Y 상관행렬은 X 변수와 Y 변수를 각각 하나 이상 선택해야 합니다.",
    action: "수치 컬럼을 X 변수 집합과 Y 변수 집합에 체크한 뒤 실행하세요.",
  },
  invalid_xy_correlation_alpha: {
    title: "유의수준 alpha 오류",
    message: "X-Y 상관행렬의 alpha는 0보다 크고 1보다 작아야 합니다.",
    action: "일반적인 시작값은 0.05입니다.",
  },
  invalid_xy_correlation_confidence_level: {
    title: "신뢰수준 오류",
    message: "X-Y 상관행렬의 신뢰수준은 0보다 크고 1보다 작아야 합니다.",
    action: "보통 0.95를 사용합니다.",
  },
  invalid_linear_model_options: {
    title: "회귀모형 옵션 형식 오류",
    message: "회귀모형 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "반응 변수, 예측변수, alpha, 신뢰수준, 추가 항 선택을 다시 확인하세요.",
  },
  linear_model_response_column_required: {
    title: "반응 변수 필요",
    message: "회귀모형은 예측하려는 숫자형 반응 변수가 필요합니다.",
    action: "반응 변수 선택칸에서 Y 또는 결과에 해당하는 숫자 컬럼을 선택하세요.",
  },
  linear_model_predictors_required: {
    title: "예측변수 필요",
    message: "회귀모형은 반응 변수를 설명할 숫자형 예측변수가 하나 이상 필요합니다.",
    action: "예측변수 목록에서 X 또는 feature에 해당하는 숫자 컬럼을 하나 이상 체크하세요.",
  },
  linear_model_response_predictor_overlap: {
    title: "반응/예측 중복",
    message: "같은 컬럼을 반응 변수와 예측변수로 동시에 사용할 수 없습니다.",
    action: "반응 변수와 예측변수에서 서로 다른 컬럼을 선택하세요.",
  },
  invalid_linear_model_alpha: {
    title: "유의수준 alpha 오류",
    message: "회귀모형의 alpha는 0보다 크고 1보다 작아야 합니다.",
    action: "일반적인 시작값은 0.05입니다.",
  },
  invalid_linear_model_confidence_level: {
    title: "신뢰수준 오류",
    message: "회귀모형의 신뢰수준은 0보다 크고 1보다 작아야 합니다.",
    action: "보통 0.95를 사용합니다.",
  },
  linear_model_residual_df_too_small: {
    title: "사용 가능한 행 부족",
    message:
      "회귀모형은 예측변수 수보다 충분히 많은 complete-case 숫자 행이 있어야 계수 검정을 계산할 수 있습니다.",
    action: "필터를 완화하거나 예측변수 수를 줄이고, 결측/문자값이 많은 컬럼을 피하세요.",
  },
  linear_model_response_constant: {
    title: "반응 변수 변동 없음",
    message: "사용된 반응 변수 값이 모두 같으면 회귀모형을 적합할 수 없습니다.",
    action: "값이 변하는 숫자형 반응 변수를 선택하거나 필터 조건을 완화하세요.",
  },
  linear_model_predictor_constant: {
    title: "예측변수 변동 없음",
    message: "사용된 예측변수 중 값이 모두 같은 컬럼이 있습니다.",
    action: "상수처럼 변하지 않는 예측변수를 제거한 뒤 다시 실행하세요.",
  },
  linear_model_factor_single_level: {
    title: "범주 수준 부족",
    message: "범주형 예측변수가 필터와 결측 제외 후 한 수준만 남았습니다.",
    action: "필터를 완화하거나 두 개 이상 수준이 남는 범주형 factor를 선택하세요.",
  },
  linear_model_factor_too_many_levels: {
    title: "범주 수준 과다",
    message: "범주형 예측변수의 수준 수가 현재 회귀모형 slice의 허용 범위를 넘었습니다.",
    action: "수준이 적은 factor를 선택하거나, 나중에 제공될 수준 병합/전처리 기능을 사용하세요.",
  },
  linear_model_predictor_column_unsupported_type: {
    title: "예측변수 타입 미지원",
    message: "회귀모형 예측변수는 현재 숫자형 또는 범주형 factor만 지원합니다.",
    action: "날짜/시간 컬럼은 제외하고, 스키마에서 범주형 factor 또는 숫자형 feature를 선택하세요.",
  },
  invalid_linear_model_quadratic_terms: {
    title: "2차항 요청 오류",
    message: "회귀모형 2차항 목록 형식이 올바르지 않습니다.",
    action: "실행 패널에서 숫자형 predictor의 2차항 체크박스를 다시 선택하세요.",
  },
  duplicate_linear_model_quadratic_term: {
    title: "2차항 중복",
    message: "같은 2차항이 요청에 두 번 들어갔습니다.",
    action: "같은 predictor의 2차항을 한 번만 선택하세요.",
  },
  invalid_linear_model_interaction_terms: {
    title: "상호작용 요청 오류",
    message: "회귀모형 상호작용 항 목록 형식이 올바르지 않습니다.",
    action: "실행 패널에서 숫자형 predictor 두 개의 상호작용 체크박스를 다시 선택하세요.",
  },
  duplicate_linear_model_interaction_term: {
    title: "상호작용 중복",
    message: "같은 상호작용 항이 요청에 두 번 들어갔습니다.",
    action: "같은 predictor 조합은 한 번만 선택하세요.",
  },
  linear_model_interaction_same_predictor: {
    title: "상호작용 항 오류",
    message: "상호작용 항은 서로 다른 두 predictor로만 만들 수 있습니다.",
    action: "서로 다른 숫자형 predictor 두 개의 조합을 선택하세요.",
  },
  linear_model_term_predictor_not_selected: {
    title: "추가 항 predictor 없음",
    message: "2차항이나 상호작용 항이 현재 선택된 예측변수가 아닌 컬럼을 가리킵니다.",
    action: "예측변수와 추가 항 선택을 다시 확인하세요.",
  },
  linear_model_term_requires_numeric_predictor: {
    title: "숫자형 predictor 필요",
    message: "이번 slice의 2차항과 상호작용 항은 숫자형 predictor만 지원합니다.",
    action: "범주형 factor는 main effect로만 사용하고, 추가 항에는 숫자형 predictor를 선택하세요.",
  },
  linear_model_quadratic_term_constant: {
    title: "2차항 변동 없음",
    message: "선택한 2차항 값이 모두 같아 회귀계수를 계산할 수 없습니다.",
    action: "다른 숫자형 predictor를 선택하거나 필터 조건을 완화하세요.",
  },
  linear_model_interaction_term_constant: {
    title: "상호작용 항 변동 없음",
    message: "선택한 상호작용 항 값이 모두 같아 회귀계수를 계산할 수 없습니다.",
    action: "다른 predictor 조합을 선택하거나 필터 조건을 완화하세요.",
  },
  linear_model_design_rank_deficient: {
    title: "예측변수 선형 종속",
    message: "예측변수들이 서로 완전히 겹치거나 선형 조합이라 계수를 안정적으로 구할 수 없습니다.",
    action: "중복 컬럼이나 완전히 같은 정보를 담은 예측변수를 제거하세요.",
  },
  linear_model_residual_variance_zero: {
    title: "잔차 분산 0",
    message: "잔차가 0에 가까워 표준오차와 p-value를 안정적으로 계산할 수 없습니다.",
    action: "데이터가 완전히 맞춰지는 작은 표본인지 확인하고 예측변수 수를 줄이세요.",
  },
  linear_model_standard_error_not_finite: {
    title: "표준오차 계산 불가",
    message: "회귀 계수 표준오차가 유한한 숫자로 계산되지 않았습니다.",
    action: "상수/중복/극단 스케일 예측변수를 제거하고 다시 실행하세요.",
  },
  invalid_gage_rr_options: {
    title: "Gage R&R 옵션 형식 오류",
    message: "Gage R&R 실행 옵션의 필수 컬럼 ID나 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값, 부품, 측정자, 반복 컬럼을 다시 선택하고 preflight를 통과한 뒤 실행하세요.",
  },
  invalid_attribute_control_chart_options: {
    title: "계수형 관리도 옵션 형식 오류",
    message: "P/NP/C/U 유형, 계수 정의, 컬럼 또는 point limit 계약이 올바르지 않습니다.",
    action: "차트 유형과 불량품/결점 정의, 표본 크기/검사 기회 선택을 다시 확인하세요.",
  },
  attribute_control_chart_count_definition_mismatch: {
    title: "계수 정의 불일치",
    message: "P/NP는 불량품 수, C/U는 결점 수를 사용해야 합니다.",
    action: "집계한 값이 불량품인지 개별 결점인지 확인하고 알맞은 차트를 선택하세요.",
  },
  attribute_control_chart_count_not_finite: {
    title: "유한한 계수 필요",
    message: "결점 또는 불량품 수에 NaN이나 무한대 값을 사용할 수 없습니다.",
    action: "계수 컬럼의 비유한 값을 수정하거나 명시적 필터로 제외하세요.",
  },
  attribute_control_chart_denominator_not_finite: {
    title: "유한한 분모 필요",
    message: "표본 크기 또는 검사 기회에 NaN이나 무한대 값을 사용할 수 없습니다.",
    action: "분모 컬럼의 비유한 값을 수정하거나 명시적 필터로 제외하세요.",
  },
  attribute_control_chart_defectives_exceed_sample_size: {
    title: "불량품 수가 표본 크기 초과",
    message: "P/NP 관측의 불량품 수는 같은 행의 표본 크기보다 클 수 없습니다.",
    action: "계수와 표본 크기 컬럼 선택 및 원자료 집계를 확인하세요.",
  },
  attribute_control_chart_np_varying_sample_size: {
    title: "NP 표본 크기 불일치",
    message: "NP 관리도는 모든 유효 관측의 표본 크기가 같아야 합니다.",
    action: "표본 크기가 변한다면 P 관리도를 선택하세요.",
  },
  attribute_control_chart_c_constant_opportunity_required: {
    title: "동일 검사 기회 확인 필요",
    message: "C 관리도는 각 관측의 검사 기회나 면적이 동일해야 합니다.",
    action: "동일 기회를 확인하거나 검사 기회가 변한다면 U 관리도를 선택하세요.",
  },
  attribute_control_chart_zero_variation: {
    title: "관리한계 추정 불가",
    message: "기준선의 추정 분산이 0이라 유효한 3-sigma 관리한계를 만들 수 없습니다.",
    action: "필터와 계수 집계를 확인하고 변동이 있는 적절한 Phase I 기간을 선택하세요.",
  },
  invalid_individuals_chart_options: {
    title: "개별값 관리도 옵션 형식 오류",
    message: "개별값 관리도 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값 컬럼, 선택적 순서 컬럼, 규칙 길이, point limit을 다시 확인하세요.",
  },
  invalid_subgroup_chart_options: {
    title: "부분군 관리도 옵션 형식 오류",
    message: "부분군 관리도 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값 컬럼, 부분군 컬럼, Xbar-R/Xbar-S 선택, point limit을 다시 확인하세요.",
  },
  invalid_gage_run_chart_options: {
    title: "Gage Run Chart 옵션 형식 오류",
    message: "Gage Run Chart 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값, 부품, 측정자, 반복 컬럼, 선택적 순서 컬럼, point limit을 다시 확인하세요.",
  },
  invalid_capability_options: {
    title: "공정능력 옵션 형식 오류",
    message: "공정능력 분석 옵션의 필수 항목, spec limit 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값 컬럼, LSL/USL/target, histogram bin limit을 다시 확인하세요.",
  },
  invalid_run_chart_options: {
    title: "런 차트 옵션 형식 오류",
    message: "런 차트 실행 옵션의 필수 항목, 타입, 또는 허용되지 않은 항목이 맞지 않습니다.",
    action: "측정값 컬럼, 순서 컬럼, trend/oscillation rule 길이, runs test alpha, point limit을 다시 확인하세요.",
  },
};

const patternDetails: Array<[RegExp, AnalysisRunErrorDetails]> = [
  [
    /response_required$/,
    {
      title: "반응 변수 필요",
      message: "검정할 결과 컬럼이 선택되지 않았습니다.",
      action: "실행 패널의 반응 변수 선택칸에서 수치 또는 이진 반응 컬럼을 선택하세요.",
    },
  ],
  [
    /columns_required$/,
    {
      title: "필수 컬럼 필요",
      message: "이 메서드가 요구하는 컬럼 역할이 모두 선택되지 않았습니다.",
      action: "반응, 그룹, 전/후 측정값처럼 표시된 필수 선택칸을 모두 채우세요.",
    },
  ],
  [
    /column_not_found$/,
    {
      title: "컬럼을 찾을 수 없음",
      message: "요청한 컬럼이 현재 dataset version 스키마에 없습니다.",
      action: "스키마를 저장한 뒤 컬럼 선택을 다시 확인하세요.",
    },
  ],
  [
    /column_is_id$/,
    {
      title: "ID 컬럼 사용 불가",
      message: "ID 역할 컬럼은 분석값으로 쓰지 않습니다.",
      action: "측정값, 반응, 그룹 컬럼을 선택하거나 스키마 role을 다시 확인하세요.",
    },
  ],
  [
    /column_not_numeric$/,
    {
      title: "수치 컬럼 필요",
      message: "선택한 분석은 숫자로 계산 가능한 컬럼이 필요합니다.",
      action: "스키마의 data type이 integer 또는 decimal인 컬럼을 선택하세요.",
    },
  ],
  [
    /same_.*column/,
    {
      title: "같은 컬럼 중복 선택",
      message: "서로 다른 역할에 같은 컬럼을 동시에 사용할 수 없습니다.",
      action: "반응과 그룹, 전과 후처럼 역할마다 다른 컬럼을 선택하세요.",
    },
  ],
  [
    /invalid_.*alpha$/,
    {
      title: "유의수준 alpha 오류",
      message: "alpha는 검정을 얼마나 엄격하게 볼지 정하는 숫자입니다.",
      action: "대부분의 검정에서는 0보다 크고 1보다 작은 값을 쓰며, 보통 0.05로 시작합니다.",
    },
  ],
  [
    /invalid_.*confidence_level$/,
    {
      title: "신뢰수준 오류",
      message: "신뢰수준은 0과 1 사이의 숫자여야 합니다.",
      action: "보통 0.95를 사용합니다.",
    },
  ],
  [
    /event_level_required$/,
    {
      title: "사건 수준 필요",
      message: "비율 검정은 어떤 값이 사건인지 알아야 합니다.",
      action: "예/아니오 데이터라면 사건 수준에 예, yes, 1 등 사건으로 볼 값을 입력하세요.",
    },
  ],
  [
    /n_too_small$/,
    {
      title: "사용 가능한 데이터 부족",
      message: "결측, 비숫자 값, 필터 제외 후 계산에 필요한 행이 부족합니다.",
      action: "반응/그룹 컬럼과 필터 조건을 확인하고 사용 가능한 행 수를 늘리세요.",
    },
  ],
];

const fallbackDetails: AnalysisRunErrorDetails = {
  title: "분석 실행 오류",
  message: "분석을 실행하기 위한 입력 조건을 만족하지 못했습니다.",
  action: "오류 코드와 선택한 컬럼, 옵션 값을 확인하세요.",
};

export function getAnalysisRunErrorDetails(code: string): AnalysisRunErrorDetails {
  const exact = exactErrorDetails[code];
  if (exact !== undefined) {
    return exact;
  }
  const match = patternDetails.find(([pattern]) => pattern.test(code));
  return match?.[1] ?? fallbackDetails;
}
