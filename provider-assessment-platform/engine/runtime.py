"""Strict runtime for governed assessment pathways.

The original rules module remains the low-level implementation. This runtime
adds the required missing-data invariant: an absent required field is UNKNOWN,
not a documented negative finding.
"""

from __future__ import annotations

from typing import Any, Mapping

from .rules import (
    Decision,
    EvaluationContext,
    Evidence,
    PathwayConfigurationError,
    PathwayEngine as BasePathwayEngine,
    RuleEvaluationError,
    RuleEvaluator as BaseRuleEvaluator,
    RuleResult,
    TruthValue,
)


class RuleEvaluator(BaseRuleEvaluator):
    """Rule evaluator with strict tri-state handling for required fields."""

    def _op_exists(self, operand: Any, context: EvaluationContext) -> RuleResult:
        path = self._require_path(operand)
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        return RuleResult(
            TruthValue.TRUE,
            f"exists({path})=True",
            (evidence,),
        )


class PathwayEngine(BasePathwayEngine):
    """Pathway engine used by applications and validation tests."""

    def __init__(self, pathway: Mapping[str, Any]):
        super().__init__(pathway)
        self.evaluator = RuleEvaluator()


__all__ = [
    "Decision",
    "EvaluationContext",
    "Evidence",
    "PathwayConfigurationError",
    "PathwayEngine",
    "RuleEvaluationError",
    "RuleEvaluator",
    "RuleResult",
    "TruthValue",
]
