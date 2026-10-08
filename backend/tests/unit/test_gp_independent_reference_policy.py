import ast
import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scripts import generate_gp_kernel_reference as reference


def test_independent_reference_has_no_application_imports() -> None:
    tree = ast.parse(Path(reference.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(name == "app" or name.startswith("app.") for name in imports)


def test_frozen_reference_uses_exact_inputs_splits_and_seeds(monkeypatch) -> None:
    case = {
        "name": "frozen",
        "x": [[float(i), float(i * i)] for i in range(6)],
        "y": [1, 2, 4, 3, 6, 8],
    }
    splits = [[3, 0], [1, 4], [5, 2]]
    original_case, original_splits = copy.deepcopy(case), copy.deepcopy(splits)
    calls = []
    validation_calls = []

    class Model:
        kernel_ = SimpleNamespace(theta=np.asarray([0.0]))
        log_marginal_likelihood_value_ = 0.0

        def predict(self, x, *, return_std):
            assert return_std is True
            validation_calls.append(x.tolist())
            return np.zeros(len(x)), np.ones(len(x))

    def fit(x, y, preset, seed):
        calls.append((x.tolist(), y.tolist(), preset, seed))
        return Model(), np.zeros(2), np.ones(2), 0.0, 1.0

    def forbid_generation(*args, **kwargs):
        raise AssertionError("Frozen input validation must not regenerate inputs or folds")

    monkeypatch.setattr(reference, "independent_fit", fit)
    monkeypatch.setattr(reference.KFold, "split", forbid_generation)
    monkeypatch.setattr(reference.np.random, "default_rng", forbid_generation)
    result = reference.evaluate_frozen_case(case, splits, 41)

    assert case == original_case
    assert splits == original_splits
    assert result["x"] == case["x"]
    assert result["y"] == case["y"]
    assert len(calls) == len(reference.PRESETS) * 4
    for priority, preset in enumerate(reference.PRESETS):
        for fold, validation in enumerate(splits):
            training = [row for row in range(6) if row not in validation]
            assert calls[priority * 4 + fold] == (
                [case["x"][row] for row in training],
                [case["y"][row] for row in training],
                preset,
                41 + priority * 104729 + fold * 1009,
            )
            assert validation_calls[priority * 3 + fold] == [case["x"][row] for row in validation]
        assert calls[priority * 4 + 3] == (case["x"], case["y"], preset, 41 + priority * 104729)


@pytest.mark.parametrize(
    "splits",
    [
        [[0, 1], [1, 2], [4, 5]],
        [[0, 1], [2, 3], [4]],
        [[0, 1], [2, 3], [4, 6]],
        [[0, 1], [2, 3], [4, 5], []],
        [[0, 1, 2, 3, 4], [5]],
        [[False, 1], [2, 3], [4, 5]],
    ],
)
def test_frozen_reference_rejects_changed_or_invalid_fold_partitions(splits) -> None:
    case = {"name": "frozen", "x": [[float(i)] for i in range(6)], "y": list(range(6))}
    with pytest.raises(ValueError, match="partition every row exactly once"):
        reference.evaluate_frozen_case(case, splits, 41)


def test_frozen_reference_rejects_mismatched_dimensions() -> None:
    case = {"name": "frozen", "x": [[0], [1]], "y": [1, 2, 3]}
    with pytest.raises(ValueError, match="dimensions"):
        reference.evaluate_frozen_case(case, [[0], [1], [2]], 41)
