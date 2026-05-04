"""Load and list YAML validation profiles."""
from pathlib import Path
from typing import Any

import yaml

from netvalidate.config import get_settings


def list_profiles() -> list[dict[str, Any]]:
    settings = get_settings()
    base = Path(settings.profiles_dir)
    if not base.exists():
        return []
    profiles = []
    for path in sorted(base.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        profiles.append(
            {
                "name": path.stem,
                "vendor": data.get("vendor", "unknown"),
                "description": data.get("description", ""),
                "check_count": len(data.get("checks", [])),
            }
        )
    return profiles


def load_profile(name: str) -> dict[str, Any]:
    settings = get_settings()
    path = Path(settings.profiles_dir) / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {name}")
    return yaml.safe_load(path.read_text())
