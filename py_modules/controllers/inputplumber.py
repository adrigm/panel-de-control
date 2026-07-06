"""InputPlumber controller config (SteamOS: Legion Go 1/2, MSI Claw).

Real per-button remap by cooperatively driving the daemon. The remappable buttons
are read dynamically from the device's live capabilities, and an override is
applied by merging it into the device's current profile while preserving defaults.
Panel de Control stores global + per-game overrides; the active InputPlumber
profile is rebuilt from the effective override map for the current game context.
"""
from controllers import ip_profile
from controllers.ip_merge import merge_profile


def _buttons_payload(buttons: list, overrides: dict) -> list:
    return [
        {"source": cap, "label": label, "target": overrides.get(cap)}
        for (cap, label) in buttons
    ]


def get_config(store, dbus, device_key, appid=None, caps=None) -> dict:
    """Return remappable buttons and target vocabularies for the current context."""
    if caps is None:
        caps = dbus.capabilities()
    buttons = ip_profile.buttons_for(device_key, caps)
    overrides = store.effective(appid)
    global_overrides = store.effective(None)
    return {
        "kind": "remap",
        "device_known": ip_profile.is_known_device(device_key),
        "buttons": _buttons_payload(buttons, overrides),
        "global_buttons": _buttons_payload(buttons, global_overrides),
        "has_game_profile": store.has_game(appid),
        "appid": str(appid) if appid is not None else None,
        "gamepad_targets": list(ip_profile.GAMEPAD_TARGETS),
        "key_targets": list(ip_profile.KEY_TARGETS),
    }


def _apply_overrides(dbus, overrides: dict, merge=merge_profile) -> bool:
    """Rebuild the profile from the pristine default and load it."""
    if not dbus.reset_default():
        return False
    if not overrides:
        return True  # reset to the device default IS the applied state
    baseline = dbus.get_profile_yaml()
    if baseline is None:
        return False
    merged = merge(baseline, overrides)
    if not merged:
        return False
    return dbus.load_profile_yaml(merged)


def _resolve_target(scope: str, appid):
    if scope == "global":
        return "global", None
    if scope == "game" and appid is not None:
        return "game", str(appid)
    return None, None


def _active_after_set(store, target_scope, target_appid, prospective: dict, active_appid):
    active_key = str(active_appid) if active_appid is not None else None
    if target_scope == "game" and active_key == target_appid:
        return prospective
    if target_scope == "global" and not store.has_game(active_key):
        return prospective
    return store.effective(active_key)


def _active_after_reset(store, target_scope, target_appid, active_appid):
    active_key = str(active_appid) if active_appid is not None else None
    if target_scope == "game" and active_key == target_appid:
        return store.effective(None)
    if target_scope == "global" and not store.has_game(active_key):
        return {}
    return store.effective(active_key)


def reapply(store, dbus, appid=None, merge=merge_profile) -> bool:
    """Reload the InputPlumber profile for the current effective scope."""
    return _apply_overrides(dbus, store.effective(appid), merge=merge)


def set_button(
    store,
    dbus,
    device_key,
    source: str,
    targets: list,
    scope: str = "global",
    appid=None,
    active_appid=None,
    merge=merge_profile,
) -> dict:
    """Remap one physical button.

    Invalid sources are ignored. Empty/invalid targets revert the button to the
    device default for the selected scope. The store is updated only if the daemon
    accepts the effective profile for the active context.
    """
    caps = dbus.capabilities()  # read once, reused for validation and response
    valid = {cap for (cap, _label) in ip_profile.buttons_for(device_key, caps)}
    target_scope, target_appid = _resolve_target(scope, appid)
    if target_scope is None:
        return get_config(store, dbus, device_key, active_appid, caps)
    if source not in valid:
        return get_config(store, dbus, device_key, active_appid, caps)

    clean = ip_profile.sanitize_targets(targets)
    prospective = store.effective(target_appid if target_scope == "game" else None)
    if clean:
        prospective[source] = clean
    else:
        prospective.pop(source, None)

    active_overrides = _active_after_set(
        store, target_scope, target_appid, prospective, active_appid
    )
    if _apply_overrides(dbus, active_overrides, merge=merge):
        store.replace(prospective, target_scope, target_appid)
    return get_config(store, dbus, device_key, active_appid, caps)


def reset(
    store,
    dbus,
    device_key=None,
    scope: str = "global",
    appid=None,
    active_appid=None,
    merge=merge_profile,
) -> dict:
    """Reset the selected scope and reload the active effective profile."""
    target_scope, target_appid = _resolve_target(scope, appid)
    if target_scope is None:
        return get_config(store, dbus, device_key, active_appid)
    active_overrides = _active_after_reset(store, target_scope, target_appid, active_appid)
    if _apply_overrides(dbus, active_overrides, merge=merge):
        store.reset(target_scope, target_appid)
    return get_config(store, dbus, device_key, active_appid)
