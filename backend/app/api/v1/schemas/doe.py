from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class DoeFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    low: FiniteFloat
    high: FiniteFloat
    unit: str | None = Field(default=None, max_length=40)


class FactorialDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="2-level full factorial design", min_length=1, max_length=120)
    factors: list[DoeFactorRequest] = Field(min_length=2, max_length=6)
    replicates: int = Field(default=1, ge=1, le=16)
    center_points: int = Field(default=0, ge=0, le=32)
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)
    block_count: int = Field(default=1, ge=1, le=64)


class DoeFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    low: float
    high: float
    unit: str | None


class FactorialDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replicates: int = Field(ge=1)
    center_points: int = Field(ge=0)
    randomize: bool
    randomization_seed: int = Field(ge=0)
    block_count: int = Field(ge=1)


class FactorialDesignRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: int = Field(ge=1)
    center_point: bool
    block_index: int | None = Field(default=None, ge=1)
    factor_levels: dict[str, float]
    coded_levels: dict[str, int]


class DoeResponseValueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int = Field(ge=1)
    value: FiniteFloat


class DoeDesignResponsesUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    values: list[DoeResponseValueRequest] = Field(min_length=1, max_length=256)


class DoeDesignResponseValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int = Field(ge=1)
    value: float


class DoeDesignResponseSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str
    unit: str | None
    response_count: int = Field(ge=0)
    values: list[DoeDesignResponseValue]


class DoeDesignResponsesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    version_number: int = Field(ge=1)
    status: str
    responses: list[DoeDesignResponseSeries]


class FactorialDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    version_number: int = Field(ge=1)
    method_id: str
    method_version: str
    family: str
    name: str
    status: str
    created_at: str
    updated_at: str
    app_version: str
    factors: list[DoeFactorResponse]
    options: FactorialDesignOptionsResponse
    run_count: int = Field(ge=1)
    design_sha256: str
    runs: list[FactorialDesignRunResponse]
