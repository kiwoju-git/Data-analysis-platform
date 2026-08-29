import { useEffect, useRef, useState } from "react";

import type { BayesianStudyCreateRequest, BayesianStudyResponse } from "../../../api";
import {
  buildBayesianStudyRequest,
  minimumBayesianInitialDesignSize,
  type ConstraintDraft,
  type FactorDraft,
} from "../../../bayesianStudyDraft";
import { DOE_FACTOR_CAPABILITIES } from "../../../doe/factorCapabilities";

export function useBayesianStudyDraftState() {
  const [studyName, setStudyName] = useState("Sequential process study");
  const [factors, setFactors] = useState<FactorDraft[]>([
    {
      key: 1,
      factorId: "x",
      name: "Input",
      low: "-1",
      high: "1",
      unit: "",
      domainKind: "continuous",
      step: "",
      displayDecimals: "",
    },
  ]);
  const [objectiveName, setObjectiveName] = useState("Response");
  const [objectiveUnit, setObjectiveUnit] = useState("");
  const [goalType, setGoalType] = useState<
    "minimize" | "maximize" | "match_target"
  >("maximize");
  const [targetValue, setTargetValue] = useState("");
  const [targetTolerance, setTargetTolerance] = useState("");
  const [initialDesignSize, setInitialDesignSize] = useState("2");
  const [initialDesignSeed, setInitialDesignSeed] = useState("20260715");
  const [initialDesignPolicy, setInitialDesignPolicy] = useState<
    "latin_hypercube_random_cd_v1" | "sha256_counter_uniform_feasible_v1"
  >("latin_hypercube_random_cd_v1");
  const [constraints, setConstraints] = useState<ConstraintDraft[]>([]);
  const [predecessorStudyId, setPredecessorStudyId] = useState<string | null>(null);
  const [predecessorSeed, setPredecessorSeed] = useState<number | null>(null);
  const nextFactorKey = useRef(2);
  const nextConstraintKey = useRef(1);

  useEffect(() => {
    const minimum = minimumBayesianInitialDesignSize(factors.length);
    setInitialDesignSize((current) => {
      const parsed = Number(current);
      return Number.isInteger(parsed) && parsed < minimum ? String(minimum) : current;
    });
  }, [factors.length]);

  function addFactor() {
    if (factors.length >= DOE_FACTOR_CAPABILITIES.bayesianStudy) return;
    const key = nextFactorKey.current++;
    setFactors((current) => [
      ...current,
      {
        key,
        factorId: `x${key}`,
        name: `Input ${key}`,
        low: "-1",
        high: "1",
        unit: "",
        domainKind: "continuous",
        step: "",
        displayDecimals: "",
      },
    ]);
  }

  function removeFactor(key: number) {
    if (isFactorReferenced(key)) return;
    setFactors((current) => current.filter((item) => item.key !== key));
  }

  function isFactorReferenced(key: number): boolean {
    return constraints.some((constraint) => {
      const coefficient = constraint.coefficients[key];
      return coefficient !== undefined && coefficient.trim() !== "" && Number(coefficient) !== 0;
    });
  }

  function disabledReasonForFactorCount(count: number): string | null {
    if (count < 1 || count > DOE_FACTOR_CAPABILITIES.bayesianStudy) {
      return "요인 수가 지원 범위를 벗어났습니다.";
    }
    const removed = factors.slice(count);
    return removed.some((factor) => isFactorReferenced(factor.key))
      ? "제거하려는 요인을 참조하는 제약조건이 있습니다. 먼저 해당 제약조건을 수정하거나 삭제하세요."
      : null;
  }

  function resizeFactors(count: number) {
    if (disabledReasonForFactorCount(count) !== null) return;
    if (count <= factors.length) {
      setFactors((current) => current.slice(0, count));
      return;
    }
    setFactors((current) => {
      const next = [...current];
      while (next.length < count) {
        const key = nextFactorKey.current++;
        next.push({
          key,
          factorId: `x${key}`,
          name: `Input ${key}`,
          low: "-1",
          high: "1",
          unit: "",
          domainKind: "continuous",
          step: "",
          displayDecimals: "",
        });
      }
      return next;
    });
  }

  function updateFactor(key: number, field: keyof Omit<FactorDraft, "key">, value: string) {
    setFactors((current) =>
      current.map((factor) => (factor.key === key ? { ...factor, [field]: value } : factor)),
    );
  }

  function addConstraint() {
    const key = nextConstraintKey.current++;
    setConstraints((current) => [
      ...current,
      {
        key,
        constraintId: `constraint_${key}`,
        name: `Constraint ${key}`,
        coefficients: {},
        relation: "less_than_or_equal",
        bound: "0",
      },
    ]);
  }

  function removeConstraint(key: number) {
    setConstraints((current) => current.filter((item) => item.key !== key));
  }

  function updateConstraint<Field extends "constraintId" | "name" | "relation" | "bound">(
    key: number,
    field: Field,
    value: ConstraintDraft[Field],
  ) {
    setConstraints((current) =>
      current.map((constraint) =>
        constraint.key === key ? { ...constraint, [field]: value } : constraint,
      ),
    );
  }

  function updateConstraintCoefficient(key: number, factorKey: number, value: string) {
    setConstraints((current) =>
      current.map((constraint) =>
        constraint.key === key
          ? { ...constraint, coefficients: { ...constraint.coefficients, [factorKey]: value } }
          : constraint,
      ),
    );
  }

  function buildRequest(): BayesianStudyCreateRequest | string {
    const request = buildBayesianStudyRequest({
      studyName,
      factors,
      constraints,
      objectiveName,
      objectiveUnit,
      goalType,
      targetValue,
      targetTolerance,
      initialDesignSize,
      initialDesignSeed,
      initialDesignPolicy,
    });
    return typeof request === "string"
      ? request
      : { ...request, predecessor_study_id: predecessorStudyId };
  }

  function prepareSuccessor(study: BayesianStudyResponse) {
    const nextFactors = study.factors.map((factor, index) => ({
      key: index + 1,
      factorId: factor.factor_id,
      name: factor.name,
      low: String(factor.low),
      high: String(factor.high),
      unit: factor.unit ?? "",
      domainKind: factor.domain_kind ?? "continuous",
      step: factor.step == null ? "" : String(factor.step),
      displayDecimals:
        factor.display_decimals == null ? "" : String(factor.display_decimals),
    }));
    const factorKeyById = new Map(nextFactors.map((factor) => [factor.factorId, factor.key]));
    setStudyName(`${study.name} successor`);
    setFactors(nextFactors);
    setObjectiveName(study.objective.name);
    setObjectiveUnit(study.objective.unit ?? "");
    setGoalType(study.objective.goal_type);
    setTargetValue(
      study.objective.target_value === null
        ? ""
        : String(study.objective.target_value),
    );
    setTargetTolerance(
      study.objective.target_tolerance === null
        ? ""
        : String(study.objective.target_tolerance),
    );
    setInitialDesignSize(String(study.initial_design.requested_size));
    setInitialDesignSeed(String(study.initial_design.seed));
    setInitialDesignPolicy(study.initial_design.policy);
    setConstraints(
      study.constraints.map((constraint, index) => ({
        key: index + 1,
        constraintId: constraint.constraint_id,
        name: constraint.name,
        coefficients: Object.fromEntries(
          constraint.terms.flatMap((term) => {
            const key = factorKeyById.get(term.factor_id);
            return key === undefined ? [] : [[key, String(term.coefficient)]];
          }),
        ),
        relation: constraint.relation,
        bound: String(constraint.bound),
      })),
    );
    nextFactorKey.current = nextFactors.length + 1;
    nextConstraintKey.current = study.constraints.length + 1;
    setPredecessorStudyId(study.study_id);
    setPredecessorSeed(study.initial_design.seed);
  }

  function cancelSuccessor() {
    setPredecessorStudyId(null);
    setPredecessorSeed(null);
  }

  function generateNewSeed() {
    const values = new Uint32Array(1);
    crypto.getRandomValues(values);
    setInitialDesignSeed(String(values[0] & 0x7fffffff));
  }

  return {
    addConstraint,
    addFactor,
    buildRequest,
    cancelSuccessor,
    constraints,
    disabledReasonForFactorCount,
    goalType,
    factors,
    generateNewSeed,
    initialDesignSeed,
    initialDesignPolicy,
    initialDesignSize,
    isFactorReferenced,
    minimumInitialDesignSize: minimumBayesianInitialDesignSize(factors.length),
    objectiveName,
    objectiveUnit,
    predecessorSeed,
    predecessorStudyId,
    prepareSuccessor,
    removeConstraint,
    removeFactor,
    resizeFactors,
    sameSeedAsPredecessor:
      predecessorSeed !== null && Number(initialDesignSeed) === predecessorSeed,
    setGoalType,
    setInitialDesignSeed,
    setInitialDesignPolicy,
    setInitialDesignSize,
    setObjectiveName,
    setObjectiveUnit,
    setTargetTolerance,
    setTargetValue,
    setStudyName,
    studyName,
    targetTolerance,
    targetValue,
    updateConstraint,
    updateConstraintCoefficient,
    updateFactor,
  };
}
