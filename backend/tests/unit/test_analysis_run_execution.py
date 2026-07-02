from app.services.analysis_run_execution import canonical_json_bytes, row_ranges


def test_canonical_json_bytes_are_sorted_and_compact() -> None:
    assert canonical_json_bytes({"b": 2, "a": "값"}) == b'{"a":"\xea\xb0\x92","b":2}'


def test_row_ranges_compacts_contiguous_indices() -> None:
    assert row_ranges((0, 1, 2, 4, 6, 7)) == [
        {"start": 0, "end": 3},
        {"start": 4, "end": 5},
        {"start": 6, "end": 8},
    ]
