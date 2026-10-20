"""Explicit CCD coordinates; legacy bounds denote axial limits, never cube limits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Literal

CcdType = Literal["circumscribed", "inscribed", "face_centered"]


class RsmCodingError(ValueError):
    pass


@dataclass(frozen=True)
class RsmFactorCoding:
    center: float
    scale: float
    input_bounds_role: Literal["factorial", "axial", "factorial_and_axial"]
    factorial_low: float
    factorial_high: float
    axial_low: float
    axial_high: float
    alpha: float

    def payload(self) -> dict[str, float | str]:
        return asdict(self)


def factor_coding(low: float, high: float, alpha: float, ccd_type: CcdType) -> RsmFactorCoding:
    if (
        not all(isfinite(value) for value in (low, high, alpha))
        or low >= high
        or alpha < 1
        or ccd_type not in {"circumscribed", "inscribed", "face_centered"}
        or (ccd_type == "face_centered" and alpha != 1)
    ):
        raise RsmCodingError("doe_rsm_coding_invalid")
    center, half_range = low / 2 + high / 2, high / 2 - low / 2
    scale = half_range / alpha if ccd_type == "inscribed" else half_range
    values = (
        center,
        scale,
        center - scale,
        center + scale,
        center - alpha * scale,
        center + alpha * scale,
    )
    if not all(isfinite(value) for value in values) or scale <= 0:
        raise RsmCodingError("doe_rsm_coding_not_finite")
    role: Literal["factorial", "axial", "factorial_and_axial"] = (
        "factorial"
        if ccd_type == "circumscribed"
        else ("axial" if ccd_type == "inscribed" else "factorial_and_axial")
    )
    return RsmFactorCoding(center, scale, role, *values[2:], alpha)


def coded_to_actual(coding: RsmFactorCoding, value: float) -> float:
    result = coding.center + coding.scale * value
    if not isfinite(value) or not isfinite(result):
        raise RsmCodingError("doe_rsm_coordinate_not_finite")
    return float(result)


def actual_to_coded(coding: RsmFactorCoding, value: float) -> float:
    result = (value - coding.center) / coding.scale
    if not isfinite(value) or not isfinite(result):
        raise RsmCodingError("doe_rsm_coordinate_not_finite")
    return float(result)


def resolve_ccd_type(alpha_mode: str, ccd_type: CcdType | None = None) -> CcdType:
    legacy: CcdType = "face_centered" if alpha_mode == "face_centered" else "inscribed"
    if alpha_mode not in {"face_centered", "rotatable"}:
        raise RsmCodingError("doe_rsm_alpha_mode_invalid")
    if ccd_type is None:
        return legacy
    if ccd_type not in {"circumscribed", "inscribed", "face_centered"} or (
        (ccd_type == "face_centered") != (alpha_mode == "face_centered")
    ):
        raise RsmCodingError("doe_rsm_ccd_type_alpha_mode_mismatch")
    return ccd_type


def rotatable_alpha(factor_count: int, factorial_replicates: int, axial_replicates: int) -> float:
    if not 2 <= factor_count <= 5 or factorial_replicates < 1 or axial_replicates < 1:
        raise RsmCodingError("doe_rsm_replicates_invalid")
    return float((2**factor_count * factorial_replicates / axial_replicates) ** 0.25)
