import json
from typing import Any, Dict, List

from config import client, logger, OPENAI_MODEL_JSON
from schemas.registry import get_required_keys


def _value_present(form: Dict[str, Any], path: str) -> bool:
    """Check whether a dotted path has a non-empty value in the form."""
    parts = path.split(".")
    cur: Any = form
    for p in parts:
        if isinstance(cur, list):
            return len(cur) > 0
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    if cur is None:
        return False
    if isinstance(cur, str):
        return cur.strip() != ""
    if isinstance(cur, list):
        return len(cur) > 0
    return True


def compute_missing(form: Dict[str, Any], schema_id: str) -> List[str]:
    """Evaluate which required keys are missing from the form."""
    required_keys = get_required_keys(schema_id)
    return [k for k in required_keys if not _value_present(form, k)]


def compute_missing_from_schema(fields: Dict[str, Any], schema: dict) -> List[str]:
    """Evaluate which required keys are missing using a dynamic schema (flat fields)."""
    required_keys = schema.get("required_keys", [])
    missing: List[str] = []
    for k in required_keys:
        val = fields.get(k)
        if val is None:
            missing.append(k)
        elif isinstance(val, str) and val.strip() == "":
            missing.append(k)
        elif isinstance(val, list) and len(val) == 0:
            missing.append(k)
    return missing


def friendly_names_from_schema(keys: List[str], schema: dict) -> Dict[str, str]:
    """Build a map of key -> friendly name from schema property descriptions."""
    props = schema.get("properties", {})
    return {k: props[k].get("description", k) if k in props else k for k in keys}


def build_suggestions(missing: List[str]) -> List[str]:
    """Static fallback suggestions based on missing keys."""
    tips_map = {
        "afiliacion.motivoConsulta": "Indique el motivo de consulta.",
        "anamnesis.sintomasPrincipales": "Mencione los síntomas principales.",
        "diagnosticos": "Registre al menos un diagnóstico (nombre, tipo y CIE‑10 si es posible).",
        "tratamientos": "Consigne al menos un tratamiento (medicamento y dosis/indicaciones).",
    }
    return [tips_map[m] for m in missing if m in tips_map]


async def generate_contextual_suggestions(
    transcript: str,
    current_form: dict,
    recent_fragment: str,
    schema_id: str,
) -> List[str]:
    """Generate contextual, dynamic suggestions using AI."""
    missing = compute_missing(current_form, schema_id)

    missing_friendly_map = {
        "afiliacion.motivoConsulta": "motivo de consulta",
        "anamnesis.sintomasPrincipales": "síntomas principales",
        "diagnosticos": "diagnóstico",
        "tratamientos": "plan de tratamiento",
    }

    missing_friendly = [missing_friendly_map.get(m, m) for m in missing]

    system = (
        "Eres un asistente clínico inteligente. Tu tarea es generar 1-3 sugerencias CONTEXTUALES "
        "para ayudar al médico a completar la historia clínica.\n\n"

        "IMPORTANTE:\n"
        "- Las sugerencias deben ser ESPECÍFICAS al contexto de lo que se está diciendo.\n"
        "- NO solo decir 'falta X campo' - ser PROACTIVO y contextual.\n"
        "- Basarte en lo que el médico acaba de decir para sugerir el siguiente paso lógico.\n"
        "- Cada sugerencia debe ser breve (máximo 15 palabras) y accionable.\n\n"

        "EJEMPLOS DE BUENAS SUGERENCIAS:\n"
        "✓ 'Pregunte cuánto tiempo lleva con fiebre' (si mencionó fiebre)\n"
        "✓ 'Indague antecedentes de hipertensión familiar' (si mencionó presión alta)\n"
        "✓ 'Considere solicitar hemograma completo' (si hay signos de infección)\n"
        "✓ 'Registre peso y talla para calcular IMC' (si está en examen físico)\n"
        "✓ 'Especifique dosis del paracetamol' (si mencionó paracetamol sin dosis)\n\n"

        "EJEMPLOS DE MALAS SUGERENCIAS (evitar):\n"
        "✗ 'Falta el diagnóstico' (muy genérico)\n"
        "✗ 'Complete el formulario' (obvio y poco útil)\n"
        "✗ 'Registre datos del paciente' (demasiado vago)\n\n"

        "Devuelve UN ÚNICO objeto JSON con formato:\n"
        '{"suggestions": ["sugerencia 1", "sugerencia 2", ...]}\n\n'

        'Si no hay nada relevante que sugerir, devuelve: {"suggestions": []}'
    )

    context_parts = []

    if recent_fragment:
        context_parts.append(f"FRAGMENTO RECIENTE (lo que acaba de decir): {recent_fragment}")

    context_parts.append(f"\nTRANSCRIPCIÓN COMPLETA:\n{transcript[-1500:]}")
    context_parts.append(f"\n\nFORMULARIO ACTUAL (JSON):\n{json.dumps(current_form, ensure_ascii=False)}")

    if missing_friendly:
        context_parts.append(f"\n\nCAMPOS FALTANTES: {', '.join(missing_friendly)}")

    user_content = "\n".join(context_parts)

    try:
        logger.info("[SUGGESTIONS] Generating contextual suggestions...")
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_JSON,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        suggestions = data.get("suggestions", [])

        logger.info(f"[SUGGESTIONS] Generated {len(suggestions)} suggestions")
        return suggestions

    except Exception:
        logger.exception("[SUGGESTIONS] Error generating contextual suggestions")
        return build_suggestions(missing)
