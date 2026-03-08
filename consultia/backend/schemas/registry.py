import json
import os
from pathlib import Path
from typing import Any, Dict, List

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"
_cache: Dict[str, Dict[str, Any]] = {}


def _load_all() -> None:
    if _cache:
        return
    for f in _DEFINITIONS_DIR.glob("*.json"):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        _cache[data["id"]] = data


def list_schemas() -> List[Dict[str, str]]:
    _load_all()
    return [{"id": s["id"], "name": s["name"]} for s in _cache.values()]


def get_schema(schema_id: str) -> Dict[str, Any]:
    _load_all()
    entry = _cache.get(schema_id)
    if entry is None:
        raise KeyError(f"Schema '{schema_id}' not found")
    return entry


def get_json_schema(schema_id: str) -> Dict[str, Any]:
    return get_schema(schema_id)["schema"]


def get_required_keys(schema_id: str) -> List[str]:
    return get_schema(schema_id)["required_keys"]
