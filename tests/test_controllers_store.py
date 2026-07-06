import json

from controllers.store import RemapStore


LEFT = [{"gamepad": "South"}]
RIGHT = [{"key": "KeyEsc"}]


def _store(tmp_path):
    return RemapStore(str(tmp_path / "controller_remap.json"))


def test_default_is_empty_global(tmp_path):
    s = _store(tmp_path)
    assert s.effective(None) == {}
    assert s.effective("42") == {}
    assert s.has_game("42") is False


def test_migrates_legacy_flat_shape_to_global(tmp_path):
    path = tmp_path / "controller_remap.json"
    path.write_text(json.dumps({"LeftPaddle1": LEFT}))
    s = RemapStore(str(path))
    assert s.effective(None) == {"LeftPaddle1": LEFT}
    assert s.effective("42") == {"LeftPaddle1": LEFT}
    assert s.has_game("42") is False


def test_game_inherits_then_overrides(tmp_path):
    s = _store(tmp_path)
    s.set("LeftPaddle1", LEFT)
    assert s.effective("42") == {"LeftPaddle1": LEFT}
    s.set("RightPaddle1", RIGHT, "game", appid="42")
    assert s.has_game("42") is True
    assert s.effective("42") == {"LeftPaddle1": LEFT, "RightPaddle1": RIGHT}
    assert s.effective(None) == {"LeftPaddle1": LEFT}


def test_clearing_game_button_creates_profile_from_global(tmp_path):
    s = _store(tmp_path)
    s.set("LeftPaddle1", LEFT)
    s.clear("LeftPaddle1", "game", appid="42")
    assert s.has_game("42") is True
    assert s.effective("42") == {}
    assert s.effective(None) == {"LeftPaddle1": LEFT}


def test_reset_game_returns_to_global_inheritance(tmp_path):
    s = _store(tmp_path)
    s.set("LeftPaddle1", LEFT)
    s.set("RightPaddle1", RIGHT, "game", appid="42")
    s.reset("game", appid="42")
    assert s.has_game("42") is False
    assert s.effective("42") == {"LeftPaddle1": LEFT}


def test_reset_global_leaves_game_profiles_intact(tmp_path):
    s = _store(tmp_path)
    s.set("LeftPaddle1", LEFT)
    s.set("RightPaddle1", RIGHT, "game", appid="42")
    s.reset("global")
    assert s.effective(None) == {}
    assert s.effective("42") == {"LeftPaddle1": LEFT, "RightPaddle1": RIGHT}


def test_robust_load_bad_json(tmp_path):
    path = tmp_path / "controller_remap.json"
    path.write_text("{ not json")
    assert RemapStore(str(path)).effective(None) == {}
