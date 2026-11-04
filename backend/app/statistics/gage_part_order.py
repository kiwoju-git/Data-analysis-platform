"""Display ordering only; original strings remain distinct grouping identities."""

import re

_TOKENS = re.compile(r"[0-9]+|[^0-9]+")


def natural_part_id_key(value: str) -> tuple[tuple[tuple[int, int, str], ...], str]:
    tokens = []
    for token in _TOKENS.findall(value):
        if "0" <= token[0] <= "9":
            # Length/lexical comparison avoids integer limits on long digit runs.
            digits = token.lstrip("0") or "0"
            tokens.append((0, len(digits), digits))
        else:
            tokens.append((1, 0, token))
    return tuple(tokens), value
