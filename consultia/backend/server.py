# server.py
# Backend para Consult-IA
# - WebSocket /ws: recibe parciales/finales de voz a texto
# - Llama a OpenAI: (a) respuesta en streaming (tokens) y (b) JSON del formulario (schema)
# - Devuelve al cliente: assistant_token (stream), form_update (JSON), missing, suggestions
#
# Ejecutar:
#   setx OPENAI_API_KEY "tu_api_key"   (Windows, cerrar/reabrir terminal)
#   uvicorn server:app --host 0.0.0.0 --port 8001 --reload

import os, json, asyncio
from typing import Dict, Any, Optional, List
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from .constants import SCHEMA, REQUIRED_KEYS

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
    tips_map = {
        "afiliacion.motivoConsulta": "Indique el motivo de consulta.",
        "anamnesis.sintomasPrincipales": "Mencione los síntomas principales.",
        "diagnosticos": "Registre al menos un diagnóstico (nombre, tipo y CIE‑10 si es posible).",
        "tratamientos": "Consigne al menos un tratamiento (medicamento y dosis/indicaciones).",
    }
    return [tips_map[m] for m in missing if m in tips_map]

# ------------------ OpenAI helpers ------------------

async def stream_summary(ws: WebSocket, transcript: str):
    """Envía respuesta de IA en streaming (token a token) a partir del transcript acumulado."""
    system = (
        "Eres un asistente clínico. Resume en 2–4 líneas lo más relevante del caso: "
        "motivo de consulta, síntomas clave, hallazgos, y si falta información para la historia clínica. "
        "No inventes datos y mantén tono profesional."
    )
    # notifica al frontend que reinicia el stream
    logger.info(f"[AI] stream_summary ENTER len={len(transcript)}") 

    await ws.send_json({"type": "assistant_reset"})

    logger.info("[AI] assistant_reset SENT")   
    # llamada con stream
    stream = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": transcript}
        ],
        temperature=0.2,
        stream=True
    )
    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.get("content")
        except Exception:
            delta = None
        if delta:
            await ws.send_json({"type": "assistant_token", "delta": delta})

async def extract_form_incremental(current_form: dict, new_fragment: str) -> dict:
    sys = (
        "Eres un asistente clínico. Tu tarea es mantener un objeto JSON de historia clínica "
        "ACTUALIZADO en tiempo real. "
        "Tienes el objeto JSON actual y un fragmento de transcript. "
        "Debes devolver un objeto JSON COMPLETO que siga EXACTAMENTE el schema proporcionado, "
        "actualizado con la información del fragmento. "
        "No inventes nada. Si el fragmento no aporta información nueva, devuelve el mismo objeto sin cambios. "
        "Devuelve SOLO JSON válido."
    )

    user = {
        "tarea": "Actualizar el formulario de historia clínica.",
        "instrucciones": "Usa el schema para asegurarte de la estructura. Devuelve el objeto JSON completo.",
        "json_schema": SCHEMA,
        "current_form": current_form,
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
    updated_form = json.loads(content)

    # Deep merge in case GPT omits fields
    def deep_merge(old: dict, new: dict) -> dict:
        result = old.copy()
        for k, v in new.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    return deep_merge(current_form, updated_form)


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

@app.get("/health")
def health():
    ok = bool(OPENAI_API_KEY)
    return JSONResponse({"ok": ok, "model_text": OPENAI_MODEL_TEXT, "model_json": OPENAI_MODEL_JSON})

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = ws.query_params.get("session") or "default"
    state = sessions.setdefault(session_id, {"final": "", "partial": "", "last_form": {}, "json_state": {}})

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
                        asyncio.create_task(stream_summary(ws, state["final"]))
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
        updated_form = await extract_form_incremental(prev_form, fragment)
        missing = compute_missing(updated_form)
        suggestions = build_suggestions(missing)

        await ws.send_json({
            "type": "form_update",
            "form": updated_form,
            "missing": missing,
            "suggestions": suggestions
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
    

# ------------------ Main ------------------

if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")

if __name__ == "__main__":
    # Permite: python server.py (útil en desarrollo)
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
