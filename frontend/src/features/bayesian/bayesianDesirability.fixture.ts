import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { DesirabilityQ1Batch, DesirabilityQ1Calculation, DesirabilityQ1Review, DesirabilityBatchCalculation, DesirabilityBatchReview, DesirabilityOrderedBatch } from "../../api/types/bayesianDesirability";

// Synthetic presentation/ownership fixture, not statistical reference evidence.
export function desirabilityFixture(id = "study-vector") {
  const study = {
    study_id: id, study_version_id: `${id}-version`, study_schema_version: 5, method_id: "doe.bayesian_optimization", method_version: "0.9.0",
    name: "Synthetic vector", status: "active", definition_sha256: "d".repeat(64),
    objective: { name: "Synthetic goals", goal_type: "desirability", observation_policy: "complete_response_vector", curve_policy: "derringer_suich_linear_v1",
      unit: null, direction: null, target_value: null, target_tolerance: null,
      responses: [{ response_id: "yield", name: "Yield <raw>", unit: "mg", goal: "maximize", lower: 0, target: 1, upper: null, importance: 1 },
        { response_id: "cost", name: "Cost", unit: "USD", goal: "minimize", lower: null, target: 1, upper: 2, importance: 1 }] },
    factors: [{ factor_id: "x", name: "Temperature", low: 0, high: 1, unit: "C", order: 0, scaling_rule: "linear_0_1" }],
    trials: [0, 1].map(index => ({ trial_id: `${id}-trial-${index}`, study_version_id: `${id}-version`, trial_number: index + 1,
      state: "completed", origin: "initial_design", objective_value: null, response_values: { yield: index, cost: 2 - index },
      actual_coordinates: { x: index }, normalized_coordinates: { x: index }, coordinates_sha256: "c".repeat(64), created_at: "2026-11-08", closed_at: "2026-11-08" })),
    trial_count: 2, completed_trial_count: 2, pending_trial_count: 0, abandoned_trial_count: 0, recommendation_hard_trial_limit: 200,
    recommendation_available: true, recommendation_blockers: [],
    observation_history: { history_revision_id: `${id}-history`, observation_history_sha256: "a".repeat(64) },
  } as unknown as BayesianStudyResponse;
  if (study.objective.goal_type !== "desirability") throw new Error("fixture_mode");
  const moments = { mean: .4, variance: .02, second_moment: .18, estimated_absolute_error: 1e-12, normal_tail_bound: 1e-20, integration_evaluations: 80 };
  const calculation: DesirabilityQ1Calculation = {
    schema_version: 4, batch_size: 1, policy: "independent_latent_desirability_beta_ei_v1", objective: { responses: study.objective.responses },
    shared_model: { schema_version: 5, policy_version: 1, factor_ids: ["x"], response_ids: ["yield", "cost"],
      curve_policy: "derringer_suich_linear_v1", moment_policy: "independent_latent_gaussian_split_quadrature_v1", independence_assumption: true,
      normalized_importance: [{ response_id: "yield", weight: .5 }, { response_id: "cost", weight: .5 }],
      response_models: ["yield", "cost"].map(response_id => ({ response_id,
        observation_view: { mode: "retain_raw", raw_observation_count: 2, unique_condition_count: 2, effective_training_count: 2, groups: [],
          nearby_diagnostics: { changes_training_data: false, units: "normalized", tolerances: null, groups: [] } },
        model: { schema_version: 4, policy_version: "bo_noise_latent_kernels_v3", factor_ids: ["x"],
          signal_kernel: { kind: "constant_times_radial_ard", family: "matern_5_2", convention: "radial_scaled_euclidean_v1", coordinate_system: "factor_bounds_normalized_0_1",
            initial_amplitude: 1, initial_length_scales: [1], amplitude: 1, length_scales: [.5], amplitude_bounds: [.01, 100], length_scale_bounds: [.01, 100] },
          noise: { mode: "estimate", initial_variance_scaled: .01, bounds_scaled: [1e-6, 1], fixed_sd_raw: null, fitted_variance_scaled: .01 },
          observation_noise_sd_raw: .1, jitter: 1e-8, normalization: { mean: 1, scale: 1, ddof: 0, direction_multiplier: 1 },
          optimizer: { name: "L-BFGS-B", optimized: true, seed: 42, restarts: 0, evaluations: 10, starts: [{ success: true, termination_reason: "converged" }] },
          log_marginal_likelihood: -1, raw_observation_count: 2, effective_training_count: 2, training_group_counts: [1, 1], fit_elapsed_ms: 10, package_versions: {},
        } })),
    },
    incumbent: { policy: "max_posterior_expected_desirability_at_observed_coordinates_v1", best_observed_desirability: .6,
      best_observed_trial_id: study.trials[1].trial_id, latent_incumbent_value: .5, latent_incumbent_trial_id: study.trials[1].trial_id,
      latent_incumbent_normalized_coordinates: { x: 1 }, observed_trial_desirabilities: [], training_posterior_desirabilities: [] },
    observation_view: { mode: "retain_raw", raw_observation_count: 2, unique_condition_count: 2, unique_coordinate_count: 2, effective_training_count: 2, groups: [] },
    items: [{ rank: 1, actual_coordinates: { x: .4 }, normalized_coordinates: { x: .4 },
      response_predictions: [{ response_id: "cost", mean_raw: 1000000000001, latent_standard_deviation_raw: .000001, predictive_standard_deviation_raw: .000002 },
        { response_id: "yield", mean_raw: 1e-8, latent_standard_deviation_raw: 2e-8, predictive_standard_deviation_raw: 3e-8 }],
      desirability_moments: moments, acquisition: { kind: "desirability_beta_expected_improvement", value: .02, threshold: .51, distribution: "beta_moment_match", alpha: 4.4, beta: 6.6, xi_desirability: .01 },
      nearest_existing_distance: .4, constraint_evaluations: [] }],
    search_budget: { max_evaluations_total: 256, evaluations_consumed: 32, evaluation_unit: "candidate_with_all_response_desirability_moments",
      posterior_evaluations: 68, integrand_evaluations: 1280, response_fit_count: 2, model_max_evaluations_total: 1000, model_evaluations_consumed: 20,
      final_factorizations: 2, time_budget_ms: 60000, elapsed_ms: 100, searches: [], termination_reason: "search_completed" },
    warnings: [], limitations: ["bayesian_desirability_curve_not_jmp_equivalent"],
  };
  const review: DesirabilityQ1Review = { schema_version: 2, review_id: `${id}-review`, study_id: study.study_id,
    study_version_id: study.study_version_id, source_history_revision_id: study.observation_history.history_revision_id,
    source_observation_history_sha256: study.observation_history.observation_history_sha256, config_sha256: "f".repeat(64), expires_at: "2026-11-08T23:59:59Z", calculation };
  const trial = { ...study.trials[0], trial_id: `${id}-pending`, trial_number: 3, origin: "recommendation" as const, state: "pending" as const,
    response_values: undefined, objective_value: null, actual_coordinates: { x: .4 }, normalized_coordinates: { x: .4 }, closed_at: null };
  const batch: DesirabilityQ1Batch = { study_id: review.study_id, study_version_id: review.study_version_id,
    source_history_revision_id: review.source_history_revision_id, source_observation_history_sha256: review.source_observation_history_sha256,
    config_sha256: review.config_sha256, calculation, method_id: "doe.bayesian_optimization", method_version: "0.9.0",
    result_schema_version: 4, config_schema_version: 4, model_schema_version: 5, item_schema_version: 3, batch_size: 1,
    batch_id: review.review_id, definition_sha256: study.definition_sha256, batch_policy: "independent_latent_desirability_beta_ei_v1",
    items: [{ item_id: `${id}-item`, batch_id: review.review_id, rank: 1, trial, current_trial: trial }], result_sha256: "b".repeat(64),
    created_at: "2026-11-08T00:00:00Z", is_latest: true, batch_state: "pending", requested_total_trial_budget: 40,
    provenance: { app_version: "0.1.0", python_version: "3.10", platform: "synthetic", build_commit: null, package_versions: {} } };
  return { study, calculation, review, batch };
}

export function desirabilityBatchFixture(id = "study-batch", size = 2) {
  const original = desirabilityFixture(id);
  // Presentation/ownership only: the proof arrays are deliberately not numerical reference data.
  const calculation: DesirabilityBatchCalculation = {
    ...original.calculation, schema_version: 5, batch_size: size, policy: "conditional_mc_desirability_beta_marginal_v1",
    batch_options: { sample_count: 64, max_moment_evaluations: 8192, min_batch_distance_normalized: 0 },
    items: Array.from({ length: size }, (_, index) => ({ ...structuredClone(original.calculation.items[0]), rank: index + 1,
      actual_coordinates: { x: (index + 1) / (size + 1) }, normalized_coordinates: { x: (index + 1) / (size + 1) },
      nearest_selected_distance: index ? 1 / (size + 1) : null,
      planning: { score: .02 / (index + 1), mc_standard_error: index ? .0001 : 0,
        conditional_variance_raw: { yield: 1e-16, cost: 1e-12 }, search_seed: 42 + index,
        sampler: { policy_version: "conditional_mc_desirability_beta_marginal_v1", root_seed: 42,
          response_sample_seeds: { yield: "1", cost: "2" }, batch_step: index, requested_sample_count: 64, effective_sample_count: index ? 64 : 0,
          conditioned_on_selected_ranks: Array.from({ length: index }, (_, i) => i + 1), baseline_threshold: .51,
          representative_prediction_source: "completed_observations_base_posterior", common_random_numbers: true,
          response_independence_assumption: true, score_is_exact_joint_ei: false, mc_standard_error_excludes_beta_approximation_error: true,
          covariance_adjustment_is_measurement_noise: false, selected_covariance: {}, moment_evaluation_unit: "joint_response_desirability_moments",
          max_moment_evaluations: 8192, moment_evaluations: 40, response_moment_evaluations: 80, integration_evaluations: 200,
          candidate_evaluations: 32, exact_selected_evaluations: 0 }, proof: { response_proofs: {}, thresholds: [], sample_moments: [] },
      } })),
    search_budget: { ...original.calculation.search_budget, max_evaluations_total: 1024,
      max_moment_evaluations: 8192, moment_evaluations: 1200, incumbent_moment_evaluations: 2,
      response_moment_evaluations: 2400, initial_pool_upper_bound_per_step: 32, preflight_moment_allowance: 2400 },
  };
  const review: DesirabilityBatchReview = { ...original.review, schema_version: 3, calculation };
  const batch: DesirabilityOrderedBatch = { ...original.batch, method_version: "0.10.0", result_schema_version: 5,
    config_schema_version: 5, item_schema_version: 4, batch_size: size, batch_policy: calculation.policy, calculation,
    items: calculation.items.map((candidate, index) => {
      const trial = { ...original.batch.items[0].trial, trial_id: `${id}-pending-${index}`, trial_number: 3 + index,
        actual_coordinates: { ...candidate.actual_coordinates }, normalized_coordinates: { ...candidate.normalized_coordinates } };
      return { ...original.batch.items[0], item_id: `${id}-item-${index}`, rank: index + 1, trial, current_trial: structuredClone(trial) };
    }) };
  return { study: original.study, calculation, review, batch };
}
