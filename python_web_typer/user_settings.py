"""
User overrides of the per-platform settings, saved as JSON by the GUI.

config.py holds the defaults and applies this file at import, so the CLI and the
GUI share the same settings. Only the per-platform dicts are editable; they are
updated in place, so modules that imported them see the changes immediately.
"""

import json
import logging
import os
from typing import Any, Dict, MutableMapping

from .humanize import Humanized

__all__ = ["EDITABLE_SETTINGS", "load_user_settings", "save_user_settings"]

logger = logging.getLogger(__name__)

# Names of the config dicts {platform: value or {key: value}} the user can edit
EDITABLE_SETTINGS = (
    "OWN_ACCOUNTS",
    "AUTO_FOLLOW",
    "AUTO_UNFOLLOW",
    "AUTO_LIKE",
    "AUTO_CHAT",
    "AUTO_OWN_POSTS",
)

_HUMANIZED_KEY = "__humanized__"


def _encode(value: Any) -> Any:
    if isinstance(value, Humanized):
        return {_HUMANIZED_KEY: [value.mean, value.max, value.min]}
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {_HUMANIZED_KEY}:
            return Humanized(*value[_HUMANIZED_KEY])
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


def load_user_settings(path: str, config: MutableMapping[str, Any]) -> None:
    """Applies the overrides saved at `path` onto the `config` module namespace."""
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = _decode(json.load(f))
    except (OSError, ValueError, TypeError) as e:
        logger.error("Ignoring unreadable user settings %s: %s", path, e)
        return

    for name in EDITABLE_SETTINGS:
        target = config[name]
        for platform, value in data.get(name, {}).items():
            if isinstance(value, dict) and isinstance(target.get(platform), dict):
                target[platform].update(value)
            else:
                target[platform] = value


def save_user_settings(path: str, config: MutableMapping[str, Any]) -> None:
    """Writes the current per-platform settings of the `config` namespace to `path`."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data: Dict[str, Any] = {name: _encode(config[name]) for name in EDITABLE_SETTINGS}
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)  # atomic: never leaves a half-written file
