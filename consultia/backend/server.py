# server.py
# Backend para Consult-IA
# - WebSocket /ws: recibe parciales/finales de voz a texto
# - Llama a OpenAI: (a) respuesta en streaming (tokens) y (b) JSON del formulario (schema)
# - Devuelve al cliente: assistant_token (stream), form_update (JSON), missing, suggestions
#
# Ejecutar:
#   setx OPENAI_API_KEY "tu_api_key"   (Windows, cerrar/reabrir terminal)
#   uvicorn server:app --host 0.0.0.0 --port 8001 --reload

import os, json, asyncio, base64, io
from typing import Dict, Any, Optional, List
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, logger, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from constants import SCHEMA, REQUIRED_KEYS
from PIL import Image

# SDK OpenAI nuevo (>=1.0)
from openai import OpenAI

# ------------------ Config ------------------

load_dotenv()  # lee .env si existe
logger = logging.getLogger("uvicorn.error")   # o: logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY no está definido. Establécelo antes de usar el servidor.")

# Modelos: puedes subir a gpt-4o si deseas mejor razonamiento, o bajar a mini para costo/latencia
OPENAI_MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini")   # texto en streaming
OPENAI_MODEL_JSON = os.getenv("OPENAI_MODEL_JSON", "gpt-4o-mini")   # structured outputs

client = OpenAI(api_key=OPENAI_API_KEY)

# Permite a tu front en http://localhost:4200 (ajusta para producción)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "../frontend/dist/consultia")

# ------------------ App ------------------

app = FastAPI(title="Consult-IA Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memoria simple por sesión (RAM)
sessions: Dict[str, Dict[str, Any]] = {}

# ------------------ Utilidades ------------------

def compute_missing(form: Dict[str, Any]) -> List[str]:
    """Evalúa campos mínimos requeridos (ruta con puntos)."""
    missing: List[str] = []

    def exists(path: str) -> bool:
        parts = path.split(".")
        cur: Any = form
        for p in parts:
            if isinstance(cur, list):
                # lista no valida para seguir por clave
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

    for k in REQUIRED_KEYS:
        if not exists(k):
            missing.append(k)

    return missing

def build_suggestions(missing: List[str]) -> List[str]:
    """Genera sugerencias basadas en campos faltantes (fallback antiguo)."""
    tips_map = {
        "afiliacion.motivoConsulta": "Indique el motivo de consulta.",
        "anamnesis.sintomasPrincipales": "Mencione los síntomas principales.",
        "diagnosticos": "Registre al menos un diagnóstico (nombre, tipo y CIE‑10 si es posible).",
        "tratamientos": "Consigne al menos un tratamiento (medicamento y dosis/indicaciones).",
    }
    return [tips_map[m] for m in missing if m in tips_map]

async def generate_contextual_suggestions(transcript: str, current_form: dict, recent_fragment: str = "") -> List[str]:
    """
    Genera sugerencias CONTEXTUALES Y DINÁMICAS basadas en:
    - Lo que se acaba de decir (recent_fragment)
    - El contexto completo (transcript)
    - El estado actual del formulario (current_form)

    Las sugerencias son proactivas y ayudan al médico a completar la consulta.
    """
    missing = compute_missing(current_form)

    # Mapeo amigable
    missing_friendly_map = {
        "afiliacion.motivoConsulta": "motivo de consulta",
        "anamnesis.sintomasPrincipales": "síntomas principales",
        "diagnosticos": "diagnóstico",
        "tratamientos": "plan de tratamiento"
    }

    missing_friendly = [missing_friendly_map.get(m, m) for m in missing]

    # Prompt para generar sugerencias contextuales
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

        "Si no hay nada relevante que sugerir, devuelve: {\"suggestions\": []}"
    )

    # Construir contexto para la IA
    context_parts = []

    if recent_fragment:
        context_parts.append(f"FRAGMENTO RECIENTE (lo que acaba de decir): {recent_fragment}")

    context_parts.append(f"\nTRANSCRIPCIÓN COMPLETA:\n{transcript[-1500:]}")  # Últimos 1500 chars

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
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,  # Un poco de creatividad para sugerencias variadas
            max_tokens=200,
            response_format={"type": "json_object"}
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        suggestions = data.get("suggestions", [])

        logger.info(f"[SUGGESTIONS] Generated {len(suggestions)} suggestions")
        return suggestions

    except Exception as e:
        logger.exception("[SUGGESTIONS] Error generating contextual suggestions")
        # Fallback: usar sugerencias basadas en campos faltantes
        return build_suggestions(missing)

# ------------------ OpenAI helpers ------------------

async def stream_summary(ws: WebSocket, transcript: str, current_form: dict = None):
    """Envía SOLO el resumen narrativo de IA en streaming (token a token).

    Este resumen debe ser puramente informativo sobre lo que se ha dicho,
    SIN mencionar campos faltantes ni sugerencias (eso va separado).

    Args:
        ws: WebSocket connection
        transcript: Transcript completo acumulado
        current_form: Estado actual del formulario (para contexto interno)
    """
    # Prompt para resumen NARRATIVO puro
    system = (
        "Eres un asistente clínico. Resume de forma NARRATIVA lo que se ha dicho en la consulta.\n"
        "- Resume en 2-3 oraciones máximo.\n"
        "- Enfócate en lo que YA se mencionó (síntomas, hallazgos, impresiones).\n"
        "- NO menciones lo que falta ni des sugerencias.\n"
        "- Sé objetivo y clínico.\n"
        "- Si no hay suficiente información, di 'Esperando más información de la consulta...'"
    )

    user_content = transcript[-2000:]  # Últimos 2000 caracteres para evitar prompts muy largos

    # notifica al frontend que reinicia el stream
    logger.info(f"[AI SUMMARY] stream_summary ENTER len={len(transcript)}")
    logger.info(f"[AI SUMMARY] Generating narrative summary (no suggestions)")

    await ws.send_json({"type": "assistant_reset"})

    # OPCIÓN 1: Intentar con streaming real
    USE_STREAMING = False  # Cambiar a True cuando funcione el streaming

    if USE_STREAMING:
        logger.info("[AI] Calling OpenAI WITH streaming...")
        stream = client.chat.completions.create(
            model=OPENAI_MODEL_TEXT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            temperature=1.0,
            max_tokens=150,
            stream=True
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
        # OPCIÓN 2: SIN streaming - enviar todo de golpe
        logger.info("[AI] Calling OpenAI WITHOUT streaming (fallback)...")
        response = client.chat.completions.create(
            model=OPENAI_MODEL_TEXT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            temperature=1.0,
            max_tokens=150
        )

        full_text = response.choices[0].message.content or ""
        logger.info(f"[AI] Got response: {full_text[:100]}...")

        # Enviar todo el texto de golpe
        if full_text:
            await ws.send_json({"type": "assistant_token", "delta": full_text})
            logger.info(f"[AI] COMPLETE. Sent full response ({len(full_text)} chars)")

async def extract_form_patch(session_id: str, new_fragment: str) -> list[dict]:
    state = sessions[session_id]

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
        "current_form": state["json_state"],
        "new_fragment": new_fragment
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content or "[]"
    try:
        patches = json.loads(content)
        if not isinstance(patches, list):
            patches = []
    except Exception:
        patches = []

    return patches

async def extract_form_incremental(session_id: str, new_fragment: str) -> dict:
    state = sessions[session_id]

    # append fragment as new user message
    state["messages"].append({
        "role": "user",
        "content": f"NUEVO FRAGMENTO: {new_fragment}. "
                   "Actualiza el objeto JSON en base a esto. "
                   "Si no hay cambios, devuelve el mismo JSON."
    })

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=state["messages"],
        temperature=0,
        response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content or "{}"
    updated_form = json.loads(content)

    # store the assistant's response in conversation for continuity
    state["messages"].append({"role": "assistant", "content": content})

    return updated_form

async def extract_form(transcript: str) -> dict:
    schema = SCHEMA

    sys = (
        "Eres un asistente clínico. Extrae SOLO los datos mencionados del transcript y "
        "devuelve EXCLUSIVAMENTE un objeto JSON válido que siga EXACTAMENTE el siguiente JSON Schema. "
        "No inventes campos ni valores. Si algo no aparece, omítelo."
    )
    user = {
        "tarea": "Completar historia clínica desde el transcript.",
        "instrucciones": "Devuelve un UNICO objeto JSON que cumpla el schema.",
        "json_schema": schema,
        "transcript": transcript
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role":"system","content": sys},
            {"role":"user","content": json.dumps(user)}  # 👈 el mensaje contiene la palabra JSON y el schema
        ],
        temperature=0,
        response_format={"type":"json_object"}          # 👈 ok, ya cumplimos el requisito
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)

# ------------------ Rutas ------------------

@app.get("/")
def root():
    return {"message": "TIMA Backend is running"}

@app.get("/health")
def health():
    ok = bool(OPENAI_API_KEY)
    return JSONResponse({"ok": ok, "model_text": OPENAI_MODEL_TEXT, "model_json": OPENAI_MODEL_JSON})

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = ws.query_params.get("session") or "default"
    state = sessions.setdefault(session_id, 
        {
            "final": "", 
            "partial": "", 
            # "last_form": {}, 
            # "json_state": {},
            "json_state": make_blank_from_schema(SCHEMA),
            "last_form": make_blank_from_schema(SCHEMA),
            "messages": []
        }
    )

    if not state["messages"]:  # first time
        state["messages"] = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente clínico. Tu tarea es mantener un objeto JSON de historia clínica "
                    "actualizado en tiempo real. Devuelve SOLO JSON válido y sigue EXACTAMENTE este schema: "
                    f"{json.dumps(SCHEMA, ensure_ascii=False)}"
                )
            },
            {
                "role": "assistant",
                "content": json.dumps(state["json_state"], ensure_ascii=False) or "{}"
            }
        ]

    try:
        while True:
            msg = await ws.receive_json()
            logger.info(f"[WS] recv: {msg}")   # <= NUEVO
            typ = msg.get("type")
            text = (msg.get("text") or "").strip()

            if typ == "partial":
                # solo mantener por si luego deseas usarlo
                state["partial"] = text

            elif typ == "final":
                if text:
                    # Concatena al buffer final con puntuación simple
                    sep = "" if state["final"].endswith((" ", "\n", ".")) else " "
                    state["final"] = (state["final"] + sep + text + ". ").strip()
                    logger.info(f"[WS] final+= session={session_id} chunk_len={len(text)} total_chars={len(state['final'])}")

                    # 1) Streaming de asistente (still inline, so doc sees live summary)
                    try:
                        # Pasar el formulario actual para que la IA sepa qué falta
                        current_form = state.get("json_state", {})
                        asyncio.create_task(stream_summary(ws, state["final"], current_form))
                    except Exception as e:
                        logger.exception("[WS] stream_summary error")
                        await ws.send_json({"type": "error", "message": f"Stream error: {e}"})

                    # 2) Form extraction (run in background, don’t block loop)
                    # Fire background task
                    # asyncio.create_task(run_form_extraction(ws, session_id, state["final"], state.get("last_form", {})))
                    new_fragment = text
                    asyncio.create_task(
                        run_incremental_update(
                            ws,
                            session_id,
                            new_fragment,
                            state.get("json_state", {}),
                            state["final"]   # 🔹 pass transcript explicitly
                        )
                    )

    except WebSocketDisconnect:
        # cliente cerrado
        return
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

async def run_incremental_update(
    ws: WebSocket,
    session_id: str,
    fragment: str,
    prev_form: dict,
    transcript: str
):
    try:
        # updated_form = await extract_form_incremental(prev_form, fragment)
        # updated_form = await extract_form_incremental(session_id, fragment)
        delta = await extract_form_delta(session_id, fragment)
        updated_form = deep_merge(prev_form, delta)
        missing = compute_missing(updated_form)

        # NUEVO: Generar sugerencias contextuales dinámicas
        suggestions = await generate_contextual_suggestions(
            transcript=transcript,
            current_form=updated_form,
            recent_fragment=fragment
        )

        await ws.send_json({
            "type": "form_update",
            "form": updated_form,
            "missing": missing,
            "suggestions": suggestions  # Ahora son sugerencias contextuales
        })

        # Compute deltas vs previous form
        deltas = compute_deltas(prev_form, updated_form)
        if deltas:
            explained = await explain_deltas(transcript, deltas)
            await ws.send_json({"type": "form_delta", "changes": explained})

        # Update session state
        sessions[session_id]["json_state"] = updated_form
        sessions[session_id]["last_form"] = updated_form

    except Exception as e:
        logger.exception("[WS] incremental update error")
        await ws.send_json({"type": "error", "message": f"Update error: {e}"})

# helper: aplanar dict a rutas "a.b.c"
def deep_merge(old: dict, new: dict) -> dict:
    result = old.copy()
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

async def run_form_extraction(ws: WebSocket, session_id: str, transcript: str, prev_form: dict):
    try:
        form = await extract_form(transcript)
        missing = compute_missing(form)
        suggestions = build_suggestions(missing)

        await ws.send_json({
            "type": "form_update",
            "form": form,
            "missing": missing,
            "suggestions": suggestions
        })

        # Compute deltas vs previous form
        deltas = compute_deltas(prev_form, form)
        if deltas:
            explained = await explain_deltas(transcript, deltas)
            await ws.send_json({"type": "form_delta", "changes": explained})

            sintomas = [c for c in explained if c["path"].startswith("anamnesis.sintomasPrincipales")]
            if sintomas:
                lista = []
                for c in sintomas:
                    v = c["value"]
                    if isinstance(v, list): lista += v
                    elif isinstance(v, str): lista.append(v)
                if lista:
                    await ws.send_json({
                        "type": "insight",
                        "label": "Síntomas",
                        "text": "; ".join(dict.fromkeys(map(str, lista)))
                    })

        # update session state
        sessions[session_id]["last_form"] = form

    except Exception as e:
        logger.exception("[WS] form extraction error")
        await ws.send_json({"type": "error", "message": f"Extraction error: {e}"})

async def extract_form_delta(session_id: str, new_fragment: str) -> dict:
    """
    Ask GPT to return only the minimal changes (delta JSON), not the full schema.
    Example output: {"afiliacion": {"nombreCompleto": "Jimena Olivares"}}
    """
    state = sessions[session_id]

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
        "current_form": state["json_state"],
        "new_fragment": new_fragment
    }

    resp = client.chat.completions.create(
        model=OPENAI_MODEL_JSON,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content or "{}"
    try:
        delta = json.loads(content)
        if not isinstance(delta, dict):
            delta = {}
    except Exception:
        delta = {}

    return delta

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

def compute_deltas(prev: dict, curr: dict):
    p = _flatten(prev); c = _flatten(curr)
    changes = []
    for path, val in c.items():
        if path not in p or p[path] != val:
            changes.append({"path": path, "value": val})
    return changes

async def explain_deltas(transcript: str, changes: list[dict]) -> list[dict]:
    """
    Devuelve una lista: [{path, value, reason, evidence}]
    Usa response_format=json_object (cumpliendo el requisito de mencionar JSON).
    Si falla, devuelve los cambios con reason/evidence vacíos.
    """
    if not changes:
        return []

    # Limitar transcript para evitar prompts gigantes
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
        "changes": changes
    }

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_JSON,          # usa el mismo que en extract_form
            messages=[
                {"role": "system", "content": system_msg},
                # 👇 el contenido incluye JSON (cumple el requisito)
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        by_path = {e.get("path"): e for e in (data.get("explanations") or []) if isinstance(e, dict) and e.get("path")}

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
        # Fallback silencioso: no trabar el flujo si la explicación falla
        logger.warning("explain_deltas failed: %s", ex)
        return [{"path": ch["path"], "value": ch.get("value"), "reason": "", "evidence": ""} for ch in changes]
    
def make_blank_from_schema(schema: dict) -> Any:
    t = schema.get("type")
    if t == "object":
        return {k: make_blank_from_schema(v) for k, v in schema.get("properties", {}).items()}
    elif t == "array":
        return []
    else:
        return None

# ------------------ Document Extraction Endpoint ------------------

@app.post("/extract-document")
async def extract_document(file: UploadFile = File(...)):
    """
    Endpoint para extraer información de documentos médicos (imágenes o PDFs).

    Usa OpenAI Vision API (GPT-4o) para:
    1. Leer el documento (imagen o PDF convertido a imagen)
    2. Extraer información estructurada según nuestro schema
    3. Retornar JSON compatible con el formulario

    Args:
        file: Archivo subido (imagen: jpg, png, etc. o PDF)

    Returns:
        JSONResponse con la estructura de datos extraída
    """
    try:
        logger.info(f"[EXTRACT-DOC] Received file: {file.filename}, content_type: {file.content_type}")

        # Leer el contenido del archivo
        contents = await file.read()

        # Determinar si es imagen o PDF
        is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith('.pdf')

        if is_pdf:
            # Para PDFs: convertir primera página a imagen
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(contents, first_page=1, last_page=1)
                if not images:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "No se pudo convertir el PDF a imagen"}
                    )

                # Convertir PIL Image a bytes
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                image_data = img_byte_arr.getvalue()

            except ImportError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "pdf2image no está instalado. Instala con: pip install pdf2image"}
                )
        else:
            # Ya es una imagen
            image_data = contents

        # Convertir a base64 para enviar a OpenAI
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Crear el prompt para Vision API
        system_prompt = """Eres un experto en digitalización de historias clínicas médicas.

Tu tarea es extraer TODA la información visible en el documento médico y estructurarla en formato JSON.

IMPORTANTE:
- Extrae TODOS los datos que veas, incluso si están incompletos
- Si un campo no está presente, omítelo del JSON (no pongas null ni cadenas vacías)
- Mantén la terminología médica original
- Para fechas, usa formato ISO (YYYY-MM-DD) si es posible
- Para arrays (síntomas, diagnósticos, tratamientos), incluye todos los items que encuentres

ESTRUCTURA ESPERADA:
{
  "afiliacion": {
    "nombreCompleto": "nombre del paciente",
    "edad": {"anios": número, "meses": número},
    "sexo": "M/F",
    "dni": "documento",
    "grupoSangre": "tipo sangre",
    "fechaHora": "fecha consulta",
    "seguro": "nombre seguro",
    "tipoConsulta": "tipo",
    "numeroSeguro": "número",
    "motivoConsulta": "motivo"
  },
  "anamnesis": {
    "tiempoEnfermedad": "duración",
    "sintomasPrincipales": ["síntoma1", "síntoma2"],
    "relato": "narrativa completa",
    "funcionesBiologicas": {
      "apetito": "estado",
      "sed": "estado",
      "orina": "estado",
      "deposiciones": "estado",
      "sueno": "estado"
    },
    "antecedentes": {
      "personales": ["antecedente1"],
      "padre": ["antecedente paterno"],
      "madre": ["antecedente materno"]
    },
    "alergias": ["alergia1"],
    "medicamentos": ["medicamento1"]
  },
  "examenClinico": {
    "signosVitales": {
      "PA": "presión arterial",
      "FC": frecuencia cardiaca (número),
      "FR": frecuencia respiratoria (número),
      "temperatura": "temperatura",
      "SpO2": "saturación",
      "IMC": "índice masa corporal",
      "peso": peso en kg,
      "talla": talla en cm
    },
    "estadoGeneral": "descripción",
    "descripcionGeneral": "hallazgos",
    "sistemas": {
      "piel": "hallazgos",
      "cabeza": "hallazgos",
      "cuello": "hallazgos",
      "torax": "hallazgos",
      "pulmones": "hallazgos",
      "corazon": "hallazgos",
      "abdomen": "hallazgos",
      "extremidades": "hallazgos",
      "neurologico": "hallazgos"
    }
  },
  "diagnosticos": [
    {"nombre": "diagnóstico", "cie10": "código", "tipo": "Presuntivo/Definitivo/Diferencial"}
  ],
  "tratamientos": [
    {"medicamento": "nombre", "dosisIndicacion": "dosis e indicaciones", "gtin": "código"}
  ],
  "firma": {
    "medico": "nombre médico",
    "colegiatura": "número colegiatura",
    "fecha": "fecha"
  }
}

Devuelve SOLO el JSON, sin explicaciones adicionales."""

        user_prompt = "Extrae toda la información de esta historia clínica y estructúrala según el formato solicitado."

        # Llamar a OpenAI Vision API
        logger.info("[EXTRACT-DOC] Calling OpenAI Vision API...")

        response = client.chat.completions.create(
            model="gpt-4o",  # gpt-4o tiene vision capabilities
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"  # high detail para mejor extracción
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0.1  # Baja temperatura para precisión
        )

        # Extraer el contenido de la respuesta
        content = response.choices[0].message.content
        logger.info(f"[EXTRACT-DOC] OpenAI response received: {len(content)} chars")

        # Parsear el JSON
        try:
            # Limpiar markdown si viene envuelto en ```json ... ```
            if content.strip().startswith("```"):
                # Extraer solo el JSON
                lines = content.strip().split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                content = '\n'.join(json_lines)

            extracted_data = json.loads(content)
            logger.info("[EXTRACT-DOC] Successfully parsed JSON")

            return JSONResponse(content={
                "success": True,
                "data": extracted_data,
                "message": "Documento procesado exitosamente"
            })

        except json.JSONDecodeError as e:
            logger.error(f"[EXTRACT-DOC] JSON parse error: {e}")
            logger.error(f"[EXTRACT-DOC] Raw content: {content}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Error al parsear la respuesta de la IA",
                    "raw_content": content
                }
            )

    except Exception as e:
        logger.exception("[EXTRACT-DOC] Unexpected error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

# ------------------ Main ------------------

if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")

if __name__ == "__main__":
    # Permite: python server.py (útil en desarrollo)
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
