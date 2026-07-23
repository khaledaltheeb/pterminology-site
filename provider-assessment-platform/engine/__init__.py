"""Deterministic provider-assessment routing engine.

This package does not diagnose. It evaluates governed pathway rules and returns
explainable next-step recommendations that require the configured human review.
"""

from .rules import (
    Decision,
    EvaluationContext,
    PathwayConfigurationError,
    PathwayEngine,
    RuleEvaluationError,
    TruthValue,
)

__all__ = [
    "Decision",
    "EvaluationContext",
    "PathwayConfigurationError",
    "PathwayEngine",
    "RuleEvaluationError",
    "TruthValue",
]
