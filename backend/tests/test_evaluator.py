from app.evaluator import deterministic_bucket, evaluate_flag, matches_rule


def test_bucket_is_stable_and_bounded():
    first = deterministic_bucket("checkout-v2", "user-123")
    second = deterministic_bucket("checkout-v2", "user-123")
    assert first == second
    assert 0 <= first < 100


def test_equals_rule():
    rule = {"attribute":"country","operator":"equals","value":"CA","enabled":True}
    assert matches_rule({"country":"CA"}, rule)
    assert not matches_rule({"country":"US"}, rule)


def test_targeting_rule_overrides_rollout():
    result, reason = evaluate_flag(flag_key="beta-search",enabled=True,rollout=0,user_id="u-1",attributes={"plan":"enterprise"},rules=[{"attribute":"plan","operator":"equals","value":"enterprise","enabled":True}])
    assert result is True
    assert reason == "targeting_rule_match"


def test_disabled_flag_always_false():
    result, reason = evaluate_flag(flag_key="off",enabled=False,rollout=100,user_id="u-1",attributes={},rules=[])
    assert result is False
    assert reason == "flag_disabled"
