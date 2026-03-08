import json
from typing import Any, Dict, List

from fastapi import WebSocket

from config import client, logger, OPENAI_MODEL_TEXT, OPENAI_MODEL_JSON
from schemas.registry import get_json_schema


# --------------- Merge / diff helpers ---------------

def deep_merge(old: dict, new: dict) -> dict:
    result = old.copy()
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(d, list):
        out[prefix] = d
    else:
        out[prefix] = d
    return out


def compute_deltas(prev: dict, curr: dict) -> List[dict]:
    p = _flatten(prev)
    c = _flatten(curr)
    changes = []
    for path, val in c.items():
        if path not in p or p[path] != val:
            changes.append({"path": path, "value": val})
    return changes


# --------------- OpenAI extraction functions ---------------

async def extract_form(transcript: str, schema_id: str) -> dict:
    schema = get_json_schema(schema_id)

    sys = (
        "Eres un asistente clínico. Extrae SOLO los datos mencionados del transcript y "
        "devuelve EXCLUSIVAMENTE un objeto JSON válido que siga EXACTAMENTE el siguiente JSON Schema. "
        "No inventes campos ni valores. Si algo no aparece, omítelo."
    )
    user = {
        "tarea": "Completar historia clínica desde el transcript.",
        "instrucciones": "Devuelve un UNICO objeto JSON que cumpla el schema.",
        "json_schema": schema,
        "transcript": transcript,
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)


async def extract_form_delta(current_form: dict, new_fragment: str, messages: list) -> dict:
    """
    Ask GPT to return only the minimal changes (delta JSON), not the full schema.
    Example output: {"afiliacion": {"nombreCompleto": "Jimena Olivares"}}
    """
    sys = (
        "Eres un asistente médico especializado que actualiza una historia clínica en formato JSON.\n\n"

        "IMPORTANTE: Debes interpretar el LENGUAJE NATURAL del médico, no solo términos técnicos exactos.\n\n"

        "EJEMPLOS DE INTERPRETACIÓN:\n"
        "- 'paciente viene por fiebre' → afiliacion.motivoConsulta: 'fiebre'\n"
        "- 'tiene tos y dolor de cabeza' → anamnesis.sintomasPrincipales: ['tos', 'dolor de cabeza']\n"
        "- 'parece ser una gripe' → diagnosticos: [{nombre: 'gripe', tipo: 'presuntivo'}]\n"
        "- 'probable faringitis' → diagnosticos: [{nombre: 'faringitis', tipo: 'presuntivo'}]\n"
        "- 'le voy a dar paracetamol' → tratamientos: [{medicamento: 'paracetamol'}]\n"
        "- 'que tome una pastilla cada 8 horas' → tratamientos: [{dosisIndicacion: 'una pastilla cada 8 horas'}]\n"
        "- 'presión 120 sobre 80' → examenClinico.signosVitales.PA: '120/80'\n"
        "- 'temperatura treinta y ocho grados' → examenClinico.signosVitales.temperatura: 38\n\n"

        "Entradas:\n"
        "  • El estado actual del objeto JSON (historia clínica).\n"
        "  • Un fragmento de texto dictado por el médico.\n"
        "  • El JSON Schema completo, con descripciones detalladas de cada campo.\n\n"

        "Instrucciones:\n"
        "1. Interpreta el SENTIDO del texto, no busques palabras clave exactas.\n"
        "2. Lee CUIDADOSAMENTE las descripciones del schema - contienen patrones de lenguaje natural a detectar.\n"
        "3. Devuelve SOLO un objeto JSON parcial con los campos que deben actualizarse.\n"
        "   - Si no hay información nueva, devuelve {}.\n"
        "4. Usa únicamente claves y estructuras que existan en el schema.\n"
        "5. Si varios campos son relevantes para el mismo texto, actualiza todos.\n"
        "6. Respeta los tipos de datos definidos en el schema (string, number, array, object, enum).\n"
        "7. Para arrays: agrega nuevos elementos sin borrar los existentes.\n"
        "8. Para enums: si no se especifica, usa el valor por defecto sugerido en la descripción.\n"
        "9. No inventes claves ni devuelvas texto adicional fuera del JSON.\n"
    )

    user = {
        "current_form": current_form,
        "new_fragment": new_fragment,
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content or "{}"
    try:
        delta = json.loads(content)
        if not isinstance(delta, dict):
            delta = {}
    except Exception:
        delta = {}

    return delta


async def extract_form_patch(current_form: dict, new_fragment: str) -> list[dict]:
    """Legacy: returns JSON Patch operations (RFC6902)."""
    sys = (
        "Eres un asistente clínico. Tu tarea es mantener un objeto JSON de historia clínica actualizado.\n"
        "Se te dará el estado actual del formulario y un fragmento de transcripción.\n"
        "Devuelve SOLO un arreglo JSON con operaciones tipo JSON Patch (RFC6902).\n"
        "Cada operación debe ser {op, path, value}.\n"
        "Usa paths estilo /afiliacion/nombreCompleto, /anamnesis/sintomasPrincipales/- para agregar.\n"
        "Si el fragmento no aporta información nueva, devuelve [].\n"
        "Devuelve SOLO JSON válido, sin explicaciones."
    )

    user = {
        "current_form": current_form,
        "new_fragment": new_fragment,
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content or "[]"
    try:
        patches = json.loads(content)
        if not isinstance(patches, list):
            patches = []
    except Exception:
        patches = []

    return patches


async def extract_form_incremental(messages: list, new_fragment: str) -> dict:
    """Legacy: appends fragment to conversation messages and returns full updated form."""
    messages.append({
        "role": "user",
        "content": (
            f"NUEVO FRAGMENTO: {new_fragment}. "
            "Actualiza el objeto JSON en base a esto. "
            "Si no hay cambios, devuelve el mismo JSON."
        ),
    })

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content or "{}"
    updated_form = json.loads(content)

    messages.append({"role": "assistant", "content": content})

    return updated_form


# --------------- Delta explanation ---------------

async def explain_deltas(transcript: str, changes: list[dict]) -> list[dict]:
    """
    Returns [{path, value, reason, evidence}].
    Falls back to empty reason/evidence on error.
    """
    if not changes:
        return []

    transcript_trim = transcript[-4000:]

    system_msg = (
        "Eres un asistente clínico. Para cada cambio de la historia clínica, "
        "devuelve SOLO un objeto JSON válido con la forma: "
        '{"explanations":[{"path":"...","reason":"...","evidence":"..."}]}. '
        "La propiedad 'reason' debe ser breve (<= 18 palabras). "
        "La propiedad 'evidence' debe ser una cita textual corta (<= 15 palabras) tomada del transcript "
        "que respalde el valor; si no hay una evidencia textual clara, deja evidence como cadena vacía. "
        "No incluyas texto adicional fuera del objeto JSON."
    )

    user_payload = {
        "tarea": "Explicar por qué se añadió/actualizó cada campo del formulario.",
        "instrucciones": "Responde con UN UNICO objeto JSON bajo la clave 'explanations'.",
        "transcript": transcript_trim,
        "changes": changes,
    }

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_JSON,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        by_path = {
            e.get("path"): e
            for e in (data.get("explanations") or [])
            if isinstance(e, dict) and e.get("path")
        }

        explained = []
        for ch in changes:
            e = by_path.get(ch["path"], {})
            explained.append({
                "path": ch["path"],
                "value": ch.get("value"),
                "reason": (e.get("reason") or "").strip(),
                "evidence": (e.get("evidence") or "").strip(),
            })
        return explained

    except Exception as ex:
        logger.warning("explain_deltas failed: %s", ex)
        return [{"path": ch["path"], "value": ch.get("value"), "reason": "", "evidence": ""} for ch in changes]


# --------------- Streaming summary ---------------

async def stream_summary(ws: WebSocket, transcript: str, current_form: dict = None):
    """Sends narrative AI summary via WebSocket (token by token or full)."""
    system = (
        "Eres un asistente clínico. Resume de forma NARRATIVA lo que se ha dicho en la consulta.\n"
        "- Resume en 2-3 oraciones máximo.\n"
        "- Enfócate en lo que YA se mencionó (síntomas, hallazgos, impresiones).\n"
        "- NO menciones lo que falta ni des sugerencias.\n"
        "- Sé objetivo y clínico.\n"
        "- Si no hay suficiente información, di 'Esperando más información de la consulta...'"
    )

    user_content = transcript[-2000:]

    logger.info(f"[AI SUMMARY] stream_summary ENTER len={len(transcript)}")
    logger.info("[AI SUMMARY] Generating narrative summary (no suggestions)")

    await ws.send_json({"type": "assistant_reset"})

    USE_STREAMING = False

    if USE_STREAMING:
        logger.info("[AI] Calling OpenAI WITH streaming...")
        stream = client.chat.completions.create(
            model=OPENAI_MODEL_TEXT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=1.0,
            max_tokens=150,
            stream=True,
        )
        logger.info("[AI] Stream created, reading tokens...")
        token_count = 0
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.get("content")
            except Exception as e:
                logger.warning(f"[AI] Error getting delta: {e}")
                delta = None
            if delta:
                token_count += 1
                logger.info(f"[AI] Token #{token_count}: {repr(delta[:30])}")
                await ws.send_json({"type": "assistant_token", "delta": delta})

        logger.info(f"[AI] COMPLETE. Sent {token_count} tokens")

    else:
        logger.info("[AI] Calling OpenAI WITHOUT streaming (fallback)...")
        response = client.chat.completions.create(
            model=OPENAI_MODEL_TEXT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=1.0,
            max_tokens=150,
        )

        full_text = response.choices[0].message.content or ""
        logger.info(f"[AI] Got response: {full_text[:100]}...")

        if full_text:
            await ws.send_json({"type": "assistant_token", "delta": full_text})
            logger.info(f"[AI] COMPLETE. Sent full response ({len(full_text)} chars)")
