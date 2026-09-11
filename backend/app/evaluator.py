from __future__ import annotations

import hashlib
from typing import Any, Iterable


def deterministic_bucket(flag_key: str, user_id: str) -> float:
    """Map a user to a stable bucket in [0, 100)."""
    digest = hashlib.sha256(f"{flag_key}:{user_id}".encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 10_000) / 100


def matches_rule(attributes: dict[str, Any], rule: dict[str, Any]) -> bool:
    actual = attributes.get(rule["attribute"])
    expected = rule["value"]
    operator = rule["operator"]
    if operator == "equals":
        return str(actual) == expected
    if operator == "in":
        return str(actual) in {item.strip() for item in expected.split(",")}
    if operator == "starts_with":
        return str(actual).startswith(expected)
    return False


def evaluate_flag(*, flag_key: str, enabled: bool, rollout: float, user_id: str, attributes: dict[str, Any], rules: Iterable[dict[str, Any]]) -> tuple[bool, str]:
    if not enabled:
        return False, "flag_disabled"
    active_rules = [rule for rule in rules if rule.get("enabled", True)]
    if active_rules and all(matches_rule(attributes, rule) for rule in active_rules):
        return True, "targeting_rule_match"
    bucket = deterministic_bucket(flag_key, user_id)
    return bucket < rollout, f"percentage_rollout:{bucket:.2f}"
