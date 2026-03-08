import json
from typing import Any, Dict, Optional

from schemas.registry import get_json_schema

DEFAULT_SCHEMA = "historia_clinica"


def make_blank_from_schema(schema: dict) -> Any:
    t = schema.get("type")
    if t == "object":
        return {k: make_blank_from_schema(v) for k, v in schema.get("properties", {}).items()}
    elif t == "array":
        return []
    else:
        return None


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create(self, session_id: str, schema_id: str = DEFAULT_SCHEMA) -> Dict[str, Any]:
        if session_id in self._sessions:
            return self._sessions[session_id]

        json_schema = get_json_schema(schema_id)
        blank = make_blank_from_schema(json_schema)
        state = {
            "schema_id": schema_id,
            "final": "",
            "partial": "",
            "json_state": blank,
            "last_form": make_blank_from_schema(json_schema),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente clínico. Tu tarea es mantener un objeto JSON de historia clínica "
                        "actualizado en tiempo real. Devuelve SOLO JSON válido y sigue EXACTAMENTE este schema: "
                        f"{json.dumps(json_schema, ensure_ascii=False)}"
                    ),
                },
                {
                    "role": "assistant",
                    "content": json.dumps(blank, ensure_ascii=False) or "{}",
                },
            ],
        }
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def update_state(self, session_id: str, updated_form: dict) -> None:
        state = self._sessions.get(session_id)
        if state:
            state["json_state"] = updated_form
            state["last_form"] = updated_form


session_manager = SessionManager()
