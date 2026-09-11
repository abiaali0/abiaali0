from app.store import FlagStore


def test_create_update_and_audit(tmp_path):
    db = tmp_path / "flags.db"
    store = FlagStore(str(db))
    created = store.create_flag({"key":"dark-mode-test","name":"Dark Mode Test","description":"Test flag","environment":"development","enabled":False,"rollout":0,"rules":[]})
    assert created["enabled"] is False
    updated = store.update_flag("dark-mode-test", {"enabled":True,"rollout":25})
    assert updated is not None
    assert updated["enabled"] is True
    assert updated["rollout"] == 25
    events = store.list_audit(10)
    assert any(event["flag_key"] == "dark-mode-test" for event in events)
