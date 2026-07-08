export interface DoeFactorRequest {
  name: string;
  low: number;
  high: number;
  unit?: string | null;
}

export interface FactorialDesignCreateRequest {
  name: string;
  factors: DoeFactorRequest[];
  replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
  block_count: number;
}

export interface DoeFactorResponse {
  name: string;
  low: number;
  high: number;
  unit: string | null;
}

export interface FactorialDesignOptionsResponse {
  replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
  block_count: number;
}

export interface FactorialDesignRunResponse {
  standard_order: number;
  run_order: number;
  replicate_index: number;
  center_point: boolean;
  block_index: number | null;
  factor_levels: Record<string, number>;
  coded_levels: Record<string, number>;
}

export interface FactorialDesignResponse {
  design_id: string;
  design_version_id: string;
  version_number: number;
  method_id: string;
  method_version: string;
  family: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  app_version: string;
  factors: DoeFactorResponse[];
  options: FactorialDesignOptionsResponse;
  run_count: number;
  design_sha256: string;
  runs: FactorialDesignRunResponse[];
}

export interface DoeResponseValueRequest {
  run_order: number;
  value: number;
}

export interface DoeDesignResponsesUpsertRequest {
  response_name: string;
  unit?: string | null;
  values: DoeResponseValueRequest[];
}

export interface DoeDesignResponseValue {
  run_order: number;
  value: number;
}

export interface DoeDesignResponseSeries {
  response_name: string;
  unit: string | null;
  response_count: number;
  values: DoeDesignResponseValue[];
}

export interface DoeDesignResponsesResponse {
  design_id: string;
  design_version_id: string;
  version_number: number;
  status: string;
  responses: DoeDesignResponseSeries[];
}
