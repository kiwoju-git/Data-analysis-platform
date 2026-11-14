export function mixtureMessages(locale: string) {
  const ko = locale === "ko";
  return {
    title: ko ? "혼합물 실험" : "Mixture study", name: ko ? "Study 이름" : "Study name",
    total: ko ? "총량" : "Total amount", unit: ko ? "공통 성분 단위" : "Common component unit",
    coding: ko ? "의사성분 코딩" : "Pseudocomponent coding", lower: ko ? "하한" : "Lower", upper: ko ? "상한" : "Upper", auto: ko ? "자동 (서버 기록)" : "Auto (recorded by server)",
    components: ko ? "혼합 성분" : "Mixture components", factorId: ko ? "요인 ID" : "Factor ID", factorName: ko ? "요인 이름" : "Factor name",
    add: ko ? "성분 추가" : "Add component", remove: ko ? "제거" : "Remove", process: ko ? "공정 요인" : "Process factors", addProcess: ko ? "공정 요인 추가" : "Add process factor",
    kind: ko ? "측정 수준" : "Measurement level", levels: ko ? "수준 (한 줄에 하나)" : "Levels (one per line)",
    seed: ko ? "시드" : "Seed", size: ko ? "초기 실험 수" : "Initial trial count", create: ko ? "Study 생성" : "Create study", cancel: ko ? "취소" : "Cancel",
    closure: ko ? "실제 성분량의 합은 총량과 같아야 합니다. 자동 정규화하거나 누락 성분을 채우지 않습니다." : "Actual component amounts must sum to the declared total. No automatic normalization or missing-component filling.",
    coVary: ko ? "성분 프로파일은 저장된 하한 초과량 또는 상한 부족량 비율을 보존하며 다른 성분과 함께 변합니다. 단독 성분 효과나 인과 효과가 아닙니다." : "Component profiles co-vary other components using the stored lower-excess or upper-deficit ratio policy. They are not isolated component effects or causal effects.",
    unsupported: ko ? "혼합물은 고정 후보 사후예측 및 maximin 계획만 지원합니다. 독립 성분 곡선, joint EI 및 JMP 수치 일치를 주장하지 않습니다." : "Mixtures support fixed-candidate posterior and maximin planning. Independent component curves, joint EI, and JMP numerical parity are not claimed.",
    invalid: ko ? "총량, 성분 경계, 공통 단위와 입력값을 확인하십시오." : "Check total, component bounds, common unit, and entered values.",
    working: ko ? "처리 중" : "Working", retry: ko ? "동일 요청 다시 확인" : "Retry exact request", refresh: ko ? "새로 고침" : "Refresh",
    fit: ko ? "대리모형 적합" : "Fit surrogate", models: ko ? "저장 모형" : "Saved models", model: ko ? "모형" : "Model", stale: ko ? "과거 출처 (확정 불가)" : "Historical source (cannot confirm)",
    candidates: ko ? "실행 가능한 후보" : "Feasible candidates", generate: ko ? "후보 생성" : "Generate candidates", candidateCount: ko ? "후보 수" : "Candidate count",
    manual: ko ? "수동 순서 선택" : "Manual ordered selection", maximin: ko ? "혼합물 maximin" : "Mixture maximin", policy: ko ? "선택 정책" : "Selection policy", batch: ko ? "배치 크기" : "Batch size", budget: ko ? "총 실험 예산" : "Total trial budget",
    review: ko ? "선택 검토" : "Review selection", confirm: ko ? "검토한 실험 확정" : "Confirm reviewed trials", confirmIntent: ko ? "표시된 출처와 조건을 확인했습니다" : "I checked the displayed source and settings",
    observations: ko ? "관측 입력" : "Observation entry", save: ko ? "관측 저장" : "Save observations", replicate: ko ? "반복 실험 추가" : "Add replicate", close: ko ? "Study 종료" : "Close study",
    profile: ko ? "전체 조건부 프로파일 평가" : "Evaluate full conditional profiler", holds: ko ? "실제 고정 조건" : "Actual holds", closureInvalid: ko ? "성분량 합 또는 경계가 맞지 않습니다." : "Component sum or bounds do not match.",
    none: ko ? "없음" : "None", selected: ko ? "선택" : "Select", eligible: ko ? "선택 가능" : "Eligible", excluded: ko ? "선택 제외" : "Excluded",
    previous: ko ? "이전" : "Previous", next: ko ? "다음" : "Next", uncertain: ko ? "결과가 불확실합니다. 출처를 변경하기 전에 새로 고쳐 확인하십시오." : "Outcome is uncertain. Refresh before changing the source.",
  };
}
