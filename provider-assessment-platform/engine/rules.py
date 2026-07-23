from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class PathwayConfigurationError(ValueError):
    """Raised when a pathway definition is internally inconsistent."""


class RuleEvaluationError(ValueError):
    """Raised when a rule uses an unsupported or malformed expression."""


class TruthValue(str, Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    @classmethod
    def from_bool(cls, value: bool) -> "TruthValue":
        return cls.TRUE if value else cls.FALSE


@dataclass(frozen=True)
class Evidence:
    path: str
    value: Any
    present: bool


@dataclass
class EvaluationContext:
    """Immutable-by-convention input for a pathway evaluation.

    `data` is a nested mapping containing the governed case record and results.
    Missing values are treated as UNKNOWN rather than as negative findings.
    """

    data: Mapping[str, Any]
    actor_roles: frozenset[str] = field(default_factory=frozenset)
    human_confirmations: frozenset[str] = field(default_factory=frozenset)

    def resolve(self, dotted_path: str) -> Evidence:
        current: Any = self.data
        if not dotted_path:
            raise RuleEvaluationError("Field path cannot be empty")

        for part in dotted_path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
                continue
            if isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
                try:
                    index = int(part)
                except ValueError:
                    return Evidence(dotted_path, None, False)
                if 0 <= index < len(current):
                    current = current[index]
                    continue
            return Evidence(dotted_path, None, False)
        return Evidence(dotted_path, current, True)


@dataclass(frozen=True)
class RuleResult:
    truth: TruthValue
    explanation: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class Decision:
    pathway_id: str
    node_id: str
    transition_id: str | None
    destination: str | None
    truth: TruthValue
    explanation_ar: str
    explanation_en: str
    source_ids: tuple[str, ...]
    requires_human_confirmation: bool
    automation_blocked: bool
    missing_fields: tuple[str, ...] = ()


class RuleEvaluator:
    """Evaluates a restricted JSON rule language without Python eval().

    Supported forms:
      {"all": [expr, ...]}
      {"any": [expr, ...]}
      {"not": expr}
      {"exists": "path.to.field"}
      {"eq": ["path.to.field", literal]}
      {"ne": ["path.to.field", literal]}
      {"in": ["path.to.field", [literal, ...]]}
      {"contains": ["path.to.list", literal]}
      {"gte": ["path.to.field", number]}
      {"gt": ["path.to.field", number]}
      {"lte": ["path.to.field", number]}
      {"lt": ["path.to.field", number]}
      {"count_gte": ["path.to.list", integer]}
      {"role": "qualified_role"}
      {"confirmed": "confirmation-id"}

    Missing fields produce UNKNOWN. UNKNOWN is never silently coerced to FALSE.
    """

    def evaluate(self, expression: Mapping[str, Any], context: EvaluationContext) -> RuleResult:
        if not isinstance(expression, Mapping) or len(expression) != 1:
            raise RuleEvaluationError("Each expression must contain exactly one operator")

        operator, operand = next(iter(expression.items()))
        handler = getattr(self, f"_op_{operator}", None)
        if handler is None:
            raise RuleEvaluationError(f"Unsupported rule operator: {operator}")
        return handler(operand, context)

    def _op_all(self, operands: Any, context: EvaluationContext) -> RuleResult:
        items = self._require_expression_list("all", operands)
        results = tuple(self.evaluate(item, context) for item in items)
        if any(item.truth is TruthValue.FALSE for item in results):
            truth = TruthValue.FALSE
        elif any(item.truth is TruthValue.UNKNOWN for item in results):
            truth = TruthValue.UNKNOWN
        else:
            truth = TruthValue.TRUE
        return self._combine("all", truth, results)

    def _op_any(self, operands: Any, context: EvaluationContext) -> RuleResult:
        items = self._require_expression_list("any", operands)
        results = tuple(self.evaluate(item, context) for item in items)
        if any(item.truth is TruthValue.TRUE for item in results):
            truth = TruthValue.TRUE
        elif any(item.truth is TruthValue.UNKNOWN for item in results):
            truth = TruthValue.UNKNOWN
        else:
            truth = TruthValue.FALSE
        return self._combine("any", truth, results)

    def _op_not(self, operand: Any, context: EvaluationContext) -> RuleResult:
        if not isinstance(operand, Mapping):
            raise RuleEvaluationError("not requires one expression")
        result = self.evaluate(operand, context)
        inverse = {
            TruthValue.TRUE: TruthValue.FALSE,
            TruthValue.FALSE: TruthValue.TRUE,
            TruthValue.UNKNOWN: TruthValue.UNKNOWN,
        }[result.truth]
        return RuleResult(inverse, f"not({result.explanation})", result.evidence)

    def _op_exists(self, operand: Any, context: EvaluationContext) -> RuleResult:
        path = self._require_path(operand)
        evidence = context.resolve(path)
        return RuleResult(
            TruthValue.from_bool(evidence.present),
            f"exists({path})={evidence.present}",
            (evidence,),
        )

    def _op_eq(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._compare("eq", operand, context, lambda left, right: left == right)

    def _op_ne(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._compare("ne", operand, context, lambda left, right: left != right)

    def _op_gte(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._numeric_compare("gte", operand, context, lambda left, right: left >= right)

    def _op_gt(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._numeric_compare("gt", operand, context, lambda left, right: left > right)

    def _op_lte(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._numeric_compare("lte", operand, context, lambda left, right: left <= right)

    def _op_lt(self, operand: Any, context: EvaluationContext) -> RuleResult:
        return self._numeric_compare("lt", operand, context, lambda left, right: left < right)

    def _op_in(self, operand: Any, context: EvaluationContext) -> RuleResult:
        path, choices = self._require_pair("in", operand)
        if not isinstance(choices, Sequence) or isinstance(choices, (str, bytes)):
            raise RuleEvaluationError("in requires a literal list as its second item")
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        return RuleResult(
            TruthValue.from_bool(evidence.value in choices),
            f"{path} in {list(choices)!r}",
            (evidence,),
        )

    def _op_contains(self, operand: Any, context: EvaluationContext) -> RuleResult:
        path, expected = self._require_pair("contains", operand)
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        if not isinstance(evidence.value, Sequence) or isinstance(evidence.value, (str, bytes)):
            raise RuleEvaluationError(f"contains expected a list at {path}")
        return RuleResult(
            TruthValue.from_bool(expected in evidence.value),
            f"{path} contains {expected!r}",
            (evidence,),
        )

    def _op_count_gte(self, operand: Any, context: EvaluationContext) -> RuleResult:
        path, expected = self._require_pair("count_gte", operand)
        if not isinstance(expected, int) or expected < 0:
            raise RuleEvaluationError("count_gte threshold must be a non-negative integer")
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        if not isinstance(evidence.value, Sequence) or isinstance(evidence.value, (str, bytes)):
            raise RuleEvaluationError(f"count_gte expected a list at {path}")
        return RuleResult(
            TruthValue.from_bool(len(evidence.value) >= expected),
            f"count({path}) >= {expected}",
            (evidence,),
        )

    def _op_role(self, operand: Any, context: EvaluationContext) -> RuleResult:
        role = self._require_nonempty_string("role", operand)
        return RuleResult(
            TruthValue.from_bool(role in context.actor_roles),
            f"actor has role {role!r}",
        )

    def _op_confirmed(self, operand: Any, context: EvaluationContext) -> RuleResult:
        confirmation = self._require_nonempty_string("confirmed", operand)
        return RuleResult(
            TruthValue.from_bool(confirmation in context.human_confirmations),
            f"human confirmation {confirmation!r}",
        )

    def _compare(self, name: str, operand: Any, context: EvaluationContext, predicate: Any) -> RuleResult:
        path, expected = self._require_pair(name, operand)
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        return RuleResult(
            TruthValue.from_bool(bool(predicate(evidence.value, expected))),
            f"{path} {name} {expected!r}",
            (evidence,),
        )

    def _numeric_compare(self, name: str, operand: Any, context: EvaluationContext, predicate: Any) -> RuleResult:
        path, expected = self._require_pair(name, operand)
        if not isinstance(expected, (int, float)) or isinstance(expected, bool):
            raise RuleEvaluationError(f"{name} threshold must be numeric")
        evidence = context.resolve(path)
        if not evidence.present:
            return self._unknown(path, evidence)
        if not isinstance(evidence.value, (int, float)) or isinstance(evidence.value, bool):
            raise RuleEvaluationError(f"{name} expected a numeric value at {path}")
        return RuleResult(
            TruthValue.from_bool(bool(predicate(evidence.value, expected))),
            f"{path} {name} {expected}",
            (evidence,),
        )

    @staticmethod
    def _unknown(path: str, evidence: Evidence) -> RuleResult:
        return RuleResult(TruthValue.UNKNOWN, f"missing({path})", (evidence,))

    @staticmethod
    def _require_expression_list(operator: str, value: Any) -> list[Mapping[str, Any]]:
        if not isinstance(value, list) or not value:
            raise RuleEvaluationError(f"{operator} requires a non-empty expression list")
        if not all(isinstance(item, Mapping) for item in value):
            raise RuleEvaluationError(f"{operator} accepts expressions only")
        return value

    @staticmethod
    def _require_pair(operator: str, value: Any) -> tuple[str, Any]:
        if not isinstance(value, list) or len(value) != 2:
            raise RuleEvaluationError(f"{operator} requires [field_path, value]")
        return RuleEvaluator._require_path(value[0]), value[1]

    @staticmethod
    def _require_path(value: Any) -> str:
        return RuleEvaluator._require_nonempty_string("field path", value)

    @staticmethod
    def _require_nonempty_string(name: str, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise RuleEvaluationError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _combine(name: str, truth: TruthValue, results: Iterable[RuleResult]) -> RuleResult:
        results_tuple = tuple(results)
        evidence = tuple(item for result in results_tuple for item in result.evidence)
        explanation = f"{name}(" + "; ".join(result.explanation for result in results_tuple) + ")"
        return RuleResult(truth, explanation, evidence)


class PathwayEngine:
    """Validates and evaluates governed pathway transitions.

    The engine returns a next-step decision only. It deliberately cannot issue a
    clinical diagnosis, alter a score, or bypass a required human confirmation.
    """

    def __init__(self, pathway: Mapping[str, Any]):
        self.pathway = pathway
        self.pathway_id = self._require_string(pathway, "id")
        self.evaluator = RuleEvaluator()
        self.nodes = self._index_nodes(pathway.get("nodes"))
        self._validate_graph()

    def evaluate_node(self, node_id: str, context: EvaluationContext) -> Decision:
        node = self._node(node_id)
        self._check_roles(node, context)

        safety_level = context.resolve("safety.level")
        if safety_level.present and safety_level.value in {"urgent", "emergency"}:
            return Decision(
                pathway_id=self.pathway_id,
                node_id=node_id,
                transition_id="system-safety-hold",
                destination="urgent-referral",
                truth=TruthValue.TRUE,
                explanation_ar="تم إيقاف المسار الروتيني بسبب مستوى سلامة يستلزم إحالة عاجلة ومراجعة بشرية.",
                explanation_en="Routine routing stopped because the safety level requires urgent referral and human review.",
                source_ids=("system-safety-policy",),
                requires_human_confirmation=True,
                automation_blocked=True,
            )

        transitions = sorted(node.get("transitions", []), key=lambda item: item["priority"])
        unknown_results: list[tuple[Mapping[str, Any], RuleResult]] = []

        for transition in transitions:
            result = self.evaluator.evaluate(transition["condition"], context)
            if result.truth is TruthValue.UNKNOWN:
                unknown_results.append((transition, result))
                continue
            if result.truth is TruthValue.FALSE:
                continue

            confirmation_required = bool(transition.get("requires_human_confirmation", False))
            confirmation_id = f"{node_id}:{transition['id']}"
            confirmed = confirmation_id in context.human_confirmations
            blocked = bool(transition.get("blocks_automation", False)) or (confirmation_required and not confirmed)

            return Decision(
                pathway_id=self.pathway_id,
                node_id=node_id,
                transition_id=transition["id"],
                destination=transition["destination"],
                truth=result.truth,
                explanation_ar=transition["explanation"]["ar"],
                explanation_en=transition["explanation"]["en"],
                source_ids=tuple(transition["source_ids"]),
                requires_human_confirmation=confirmation_required,
                automation_blocked=blocked,
            )

        if unknown_results:
            missing = sorted(
                {
                    evidence.path
                    for _, result in unknown_results
                    for evidence in result.evidence
                    if not evidence.present
                }
            )
            return Decision(
                pathway_id=self.pathway_id,
                node_id=node_id,
                transition_id=None,
                destination=None,
                truth=TruthValue.UNKNOWN,
                explanation_ar="لا يمكن تحديد الخطوة التالية قبل استكمال البيانات المطلوبة.",
                explanation_en="The next step cannot be selected until required data are completed.",
                source_ids=(),
                requires_human_confirmation=True,
                automation_blocked=True,
                missing_fields=tuple(missing),
            )

        return Decision(
            pathway_id=self.pathway_id,
            node_id=node_id,
            transition_id=None,
            destination=None,
            truth=TruthValue.FALSE,
            explanation_ar="لم تتحقق أي قاعدة انتقال؛ يلزم تطبيق سلوك الفشل المحدد ومراجعة المسار.",
            explanation_en="No transition rule matched; apply the configured failure behavior and review the pathway.",
            source_ids=(),
            requires_human_confirmation=True,
            automation_blocked=True,
        )

    def _index_nodes(self, nodes: Any) -> dict[str, Mapping[str, Any]]:
        if not isinstance(nodes, list) or not nodes:
            raise PathwayConfigurationError("Pathway must contain at least one node")
        indexed: dict[str, Mapping[str, Any]] = {}
        for node in nodes:
            if not isinstance(node, Mapping):
                raise PathwayConfigurationError("Each node must be an object")
            node_id = self._require_string(node, "id")
            if node_id in indexed:
                raise PathwayConfigurationError(f"Duplicate node id: {node_id}")
            indexed[node_id] = node
        return indexed

    def _validate_graph(self) -> None:
        start_node = self.pathway.get("entry", {}).get("start_node")
        if start_node not in self.nodes:
            raise PathwayConfigurationError(f"Unknown start node: {start_node!r}")

        for node_id, node in self.nodes.items():
            transitions = node.get("transitions")
            if not isinstance(transitions, list):
                raise PathwayConfigurationError(f"Node {node_id} transitions must be a list")
            seen_ids: set[str] = set()
            seen_priorities: set[int] = set()
            for transition in transitions:
                transition_id = self._require_string(transition, "id")
                if transition_id in seen_ids:
                    raise PathwayConfigurationError(f"Duplicate transition {transition_id} in {node_id}")
                seen_ids.add(transition_id)

                priority = transition.get("priority")
                if not isinstance(priority, int) or priority < 1:
                    raise PathwayConfigurationError(f"Invalid priority in {node_id}/{transition_id}")
                if priority in seen_priorities:
                    raise PathwayConfigurationError(f"Duplicate priority {priority} in node {node_id}")
                seen_priorities.add(priority)

                destination = self._require_string(transition, "destination")
                if destination not in self.nodes and destination != "urgent-referral":
                    raise PathwayConfigurationError(
                        f"Unknown destination {destination!r} in {node_id}/{transition_id}"
                    )
                if not isinstance(transition.get("condition"), Mapping):
                    raise PathwayConfigurationError(f"Missing rule condition in {node_id}/{transition_id}")
                if not transition.get("source_ids"):
                    raise PathwayConfigurationError(f"Transition {node_id}/{transition_id} has no source")

        global_rules = self.pathway.get("global_rules", {})
        if global_rules.get("prohibit_single_tool_conclusion") is not True:
            raise PathwayConfigurationError("Single-tool conclusions must be explicitly prohibited")

    def _check_roles(self, node: Mapping[str, Any], context: EvaluationContext) -> None:
        required = set(node.get("required_roles", []))
        if required and not required.intersection(context.actor_roles):
            raise PermissionError(
                f"Actor lacks a required role for node {node['id']}: {sorted(required)}"
            )

    def _node(self, node_id: str) -> Mapping[str, Any]:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise PathwayConfigurationError(f"Unknown node: {node_id}") from exc

    @staticmethod
    def _require_string(mapping: Mapping[str, Any], key: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PathwayConfigurationError(f"{key} must be a non-empty string")
        return value.strip()
