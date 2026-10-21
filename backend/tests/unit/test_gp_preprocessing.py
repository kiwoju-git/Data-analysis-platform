from __future__ import annotations

import json

import numpy as np
import pytest

from app.statistics.gp_preprocessing import (
    GpPredictorSpec,
    GpPreprocessingError,
    GpPreprocessor,
    fit_gp_preprocessor,
    transform_gp_rows,
    validate_encoded_gp_matrix,
)


def specs():
    return (GpPredictorSpec("numeric", "numeric"), GpPredictorSpec("category", "nominal"))


def test_training_only_numeric_scaling_and_full_category_identity():
    first, second = "X" * 121 + "-A", "X" * 121 + "-B"
    processor, x = fit_gp_preprocessor([[1, first], [2, second], [3, first]], specs())
    np.testing.assert_array_equal(x, [[-1, 0], [0, 1], [1, 0]])
    assert processor.numeric_indices == (0,)
    assert processor.categorical_indices == (1,)
    assert processor.active_categorical_indices == (1,)
    assert processor.hold_values == (2.0, first)
    transformed = transform_gp_rows(processor, [[100, second]])
    np.testing.assert_array_equal(transformed, [[98, 1]])
    assert processor.to_payload()["predictors"][1]["vocabulary"] == [first, second]


def test_numeric_strings_are_not_nominal_coerced_and_mode_ties_use_training_order():
    processor, x = fit_gp_preprocessor(
        [[1, "01"], [2, "1"], [3, "01"], [4, "1"]], specs(), standardize_numeric=False
    )
    np.testing.assert_array_equal(x[:, 0], [1, 2, 3, 4])
    np.testing.assert_array_equal(x[:, 1], [0, 1, 0, 1])
    assert processor.hold_values == (2.5, "01")
    with pytest.raises(GpPreprocessingError, match="gp_category_value_invalid"):
        transform_gp_rows(processor, [[2, 1]])


def test_unseen_fold_category_is_error_not_excluded_or_replaced():
    processor, _ = fit_gp_preprocessor([[1, "A"], [2, "A"]], specs())
    assert processor.active_categorical_indices == ()
    assert "gp_categorical_constant_training_fold" in processor.warning_codes
    with pytest.raises(GpPreprocessingError, match="gp_category_unknown"):
        transform_gp_rows(processor, [[3, "B"]])
    with pytest.raises(GpPreprocessingError, match="gp_numeric_predictor_constant"):
        fit_gp_preprocessor([[1, "A"], [1, "B"]], specs())


def test_unscaled_fold_constant_requires_explicit_legacy_policy():
    processor, x = fit_gp_preprocessor(
        [[1, "A"], [1, "B"]],
        specs(),
        standardize_numeric=False,
        allow_constant_numeric=True,
    )
    np.testing.assert_array_equal(x[:, 0], [1, 1])
    assert "gp_numeric_constant_training_fold" in processor.warning_codes
    restored = GpPreprocessor.from_payload(processor.to_payload())
    np.testing.assert_array_equal(transform_gp_rows(restored, [[1, "A"], [2, "B"]])[:, 0], [1, 2])
    with pytest.raises(GpPreprocessingError, match="gp_predictor_contract_invalid"):
        fit_gp_preprocessor([[1, "A"], [1, "B"]], specs(), allow_constant_numeric=True)


def test_safe_json_round_trip_and_numeric_npz_code_validation():
    processor, encoded = fit_gp_preprocessor([[1, "A"], [2, "B"], [4, "A"]], specs())
    payload = json.loads(json.dumps(processor.to_payload(), allow_nan=False))
    restored = GpPreprocessor.from_payload(payload)
    np.testing.assert_array_equal(
        transform_gp_rows(restored, [[1, "A"], [2, "B"], [4, "A"]]), encoded
    )
    validate_encoded_gp_matrix(restored, encoded)
    for bad in [
        np.array([[0, 0]], dtype=object),
        np.array([[0, 0.5]]),
        np.array([[0, -1]]),
        np.array([[0, 2]]),
        np.array([[np.nan, 0]]),
        np.array([[0, 0, 1]]),
    ]:
        with pytest.raises(GpPreprocessingError, match="gp_encoded_matrix_invalid"):
            validate_encoded_gp_matrix(restored, bad)
    payload["unknown"] = "not accepted"
    with pytest.raises(GpPreprocessingError, match="gp_preprocessor_payload_invalid"):
        GpPreprocessor.from_payload(payload)


@pytest.mark.parametrize("bad", [None, True, "1", float("inf"), float("nan")])
def test_numeric_inputs_must_be_explicit_finite_numbers(bad):
    with pytest.raises(GpPreprocessingError, match="gp_numeric_value_invalid"):
        fit_gp_preprocessor([[1, "A"], [bad, "B"]], specs())


def test_product_limits_and_duplicate_predictor_ids_are_explicit():
    for columns in [
        tuple(GpPredictorSpec(str(i), "numeric") for i in range(13)),
        tuple(GpPredictorSpec(str(i), "nominal") for i in range(5)),
        (GpPredictorSpec("same", "numeric"), GpPredictorSpec("same", "nominal")),
    ]:
        with pytest.raises(GpPreprocessingError, match="gp_predictor_contract_invalid"):
            fit_gp_preprocessor([[1] * len(columns), [2] * len(columns)], columns)
    with pytest.raises(GpPreprocessingError, match="gp_category_level_limit"):
        fit_gp_preprocessor(
            [[str(i)] for i in range(33)], (GpPredictorSpec("category", "nominal"),)
        )


def test_category_only_and_identity_rename_preserve_codes():
    a, encoded_a = fit_gp_preprocessor(
        [["A", "01"], ["B", "1"], ["A", "1"]],
        (GpPredictorSpec("one", "nominal"), GpPredictorSpec("two", "nominal")),
    )
    b, encoded_b = fit_gp_preprocessor(
        [["renamed beta", "X"], ["renamed alpha", "Y"], ["renamed beta", "Y"]],
        (GpPredictorSpec("one", "nominal"), GpPredictorSpec("two", "nominal")),
    )
    np.testing.assert_array_equal(encoded_a, encoded_b)
    assert a.numeric_indices == b.numeric_indices == ()


def test_restored_vocab_counts_and_holds_are_validated_not_coerced():
    processor, _ = fit_gp_preprocessor([[1, "A"], [2, "B"]], specs())
    for field, bad in [("vocabulary", ["A", "A"]), ("counts", [1, 0]), ("mode", "C")]:
        payload = processor.to_payload()
        payload["predictors"][1][field] = bad
        with pytest.raises(GpPreprocessingError, match="gp_preprocessor_payload_invalid"):
            GpPreprocessor.from_payload(payload)


def test_numeric_npz_round_trip_uses_no_pickle_and_non_ascii_path(tmp_path):
    processor, encoded = fit_gp_preprocessor([[1, "A"], [2, "B"]], specs())
    path = tmp_path / "model \uac80\uc99d.npz"
    np.savez_compressed(path, encoded_train=encoded)
    with np.load(path, allow_pickle=False) as arrays:
        validate_encoded_gp_matrix(processor, arrays["encoded_train"])
        np.testing.assert_array_equal(arrays["encoded_train"], encoded)
    object_path = tmp_path / "invalid_object.npz"
    np.savez_compressed(object_path, encoded_train=np.array([["A"]], dtype=object))
    with np.load(object_path, allow_pickle=False) as arrays:
        with pytest.raises(ValueError, match="Object arrays cannot be loaded"):
            arrays["encoded_train"]


@pytest.mark.parametrize("value", [None, "", 1, True])
def test_missing_or_non_string_nominal_values_are_not_imputed(value):
    with pytest.raises(GpPreprocessingError, match="gp_category_value_invalid"):
        fit_gp_preprocessor([[1, "A"], [2, value]], specs())
