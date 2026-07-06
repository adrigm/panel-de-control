"""Persisted controller-remap overrides (global + per-game).

Maps a source button to its user-chosen target list. Missing buttons fall back to
the device default. A game profile inherits global until it is created; once it
exists it is a complete override map for that appid. JSON, atomic write, robust
load (never raises). Migrates the old flat global-only shape.
"""
import copy
import json

from json_store import atomic_json_save


def _clean_overrides(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    out = {}
    for source, targets in raw.items():
        if isinstance(source, str) and isinstance(targets, list):
            out[source] = copy.deepcopy(targets)
    return out


class RemapStore:
    def __init__(self, path: str):
        self._path = path
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self._path) as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        # Current shape.
        if "global" in raw or "games" in raw:
            games = {}
            raw_games = raw.get("games")
            if isinstance(raw_games, dict):
                for appid, overrides in raw_games.items():
                    games[str(appid)] = _clean_overrides(overrides)
            return {"global": _clean_overrides(raw.get("global")), "games": games}
        # Legacy shape: the whole object was the global override map.
        return {"global": _clean_overrides(raw), "games": {}}

    def all(self) -> dict:
        """Back-compat alias: the global override map."""
        return copy.deepcopy(self._data["global"])

    def effective(self, appid) -> dict:
        if appid is not None and str(appid) in self._data["games"]:
            return copy.deepcopy(self._data["games"][str(appid)])
        return copy.deepcopy(self._data["global"])

    def has_game(self, appid) -> bool:
        return appid is not None and str(appid) in self._data["games"]

    def _target(self, scope: str, appid):
        if scope == "global":
            return self._data["global"]
        if scope == "game":
            if appid is None:
                raise ValueError("appid required for game scope")
            key = str(appid)
            if key not in self._data["games"]:
                self._data["games"][key] = copy.deepcopy(self._data["global"])
            return self._data["games"][key]
        raise ValueError(f"unknown scope: {scope}")

    def set(self, source: str, targets: list, scope: str = "global", appid=None) -> None:
        self._target(scope, appid)[source] = copy.deepcopy(targets)
        self._save()

    def clear(self, source: str, scope: str = "global", appid=None) -> None:
        self._target(scope, appid).pop(source, None)
        self._save()

    def replace(self, data: dict, scope: str = "global", appid=None) -> None:
        if scope == "global":
            self._data["global"] = _clean_overrides(data)
        elif scope == "game":
            if appid is None:
                raise ValueError("appid required for game scope")
            self._data["games"][str(appid)] = _clean_overrides(data)
        else:
            raise ValueError(f"unknown scope: {scope}")
        self._save()

    def reset(self, scope: str = "global", appid=None) -> None:
        if scope == "global":
            self._data["global"] = {}
        elif scope == "game":
            if appid is not None:
                self._data["games"].pop(str(appid), None)
        else:
            raise ValueError(f"unknown scope: {scope}")
        self._save()

    def _save(self) -> None:
        atomic_json_save(self._path, self._data)
