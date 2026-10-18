"""Display copies of stored group identities; never reconstruct truncated legacy values."""

from typing import cast


def full_group_names(result: dict[str, object]) -> dict[str, object]:
    def row(value: object) -> object:
        if not isinstance(value, dict):
            return value
        display = cast(dict[str, object], value.copy())
        for label, full in (
            ("group_label", "group_value"),
            ("group_1_label", "group_1_value"),
            ("group_2_label", "group_2_value"),
            ("left_group", "left_group_value"),
            ("right_group", "right_group_value"),
        ):
            if isinstance(display.get(full), str):
                display[label] = display[full]
        return display

    display = result.copy()
    if isinstance(result.get("groups"), list):
        display["groups"] = [row(group) for group in cast(list[object], result["groups"])]
    if isinstance(result.get("contrast"), dict):
        display["contrast"] = row(result["contrast"])
    for section, keys in (
        ("posthoc", ("comparisons",)),
        ("multiple_comparisons", ("groups", "pairwise_p_values", "non_overlapping_pairs")),
    ):
        value = result.get(section)
        if isinstance(value, dict):
            updated = value.copy()
            for key in keys:
                if isinstance(value.get(key), list):
                    updated[key] = [row(item) for item in value[key]]
            display[section] = updated
    return display


def has_legacy_group_labels(result: dict[str, object]) -> bool:
    groups = result.get("groups")
    return isinstance(groups, list) and any(
        isinstance(group, dict) and not isinstance(group.get("group_value"), str)
        for group in groups
    )
