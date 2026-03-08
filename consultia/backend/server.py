# server.py
# Backend para Consult-IA — thin routes only
#
# Ejecutar:
#   uvicorn server:app --host 0.0.0.0 --port 8001 --reload

import os, json, asyncio
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import (
    logger,
    OPENAI_API_KEY,
    OPENAI_MODEL_TEXT,
    OPENAI_MODEL_JSON,
    ALLOWED_ORIGINS,
    FRONTEND_PATH,
)
from schemas.registry import list_schemas
from sessions import session_manager, DEFAULT_SCHEMA

from services.form_extraction import (
    deep_merge,
    compute_deltas,
    extract_form_delta,
    extract_tab_fields,
    explain_deltas,
    stream_summary,
)
from services.suggestions import (
    compute_missing,
    generate_contextual_suggestions,
)
from services.transcription import transcribe_audio
from services.document import extract_document

# Medberos AI Integration
from integrations.medberos import (
    medberos_client,
    consultia_to_medberos_payload,
    medberos_diagnoses_to_consultia,
    medberos_exams_to_consultia,
    medberos_treatments_to_consultia,
)

# ------------------ App ------------------

app = FastAPI(title="Consult-IA Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Routes ------------------


@app.get("/")
def root():
    return {"message": "TIMA Backend is running"}


@app.get("/health")
def health():
    ok = bool(OPENAI_API_KEY)
    return JSONResponse({"ok": ok, "model_text": OPENAI_MODEL_TEXT, "model_json": OPENAI_MODEL_JSON})


@app.get("/schemas")
def schemas_list():
    return JSONResponse({"schemas": list_schemas()})


# ------------------ Transcription ------------------


@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    try:
        text = await transcribe_audio(file)
        return JSONResponse(content={"text": text})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"[WHISPER] Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ------------------ Document Extraction ------------------


@app.post("/extract-document")
async def extract_document_endpoint(file: UploadFile = File(...)):
    try:
        extracted_data = await extract_document(file)
        return JSONResponse(content={
            "success": True,
            "data": extracted_data,
            "message": "Documento procesado exitosamente",
        })
    except json.JSONDecodeError as e:
        logger.error(f"[EXTRACT-DOC] JSON parse error: {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "Error al parsear la respuesta de la IA",
        })
    except ValueError as e:
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})
    except ImportError:
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "pdf2image no está instalado. Instala con: pip install pdf2image",
        })
    except Exception as e:
        logger.exception("[EXTRACT-DOC] Unexpected error")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ------------------ Medberos AI Endpoints ------------------


@app.get("/medberos/test")
async def test_medberos():
    result = await medberos_client.test_connection()
    return JSONResponse(result)


@app.post("/medberos/predict-all")
async def predict_all_endpoint(request_data: Dict[str, Any]):
    form = request_data.get("form", {})
    doctor_comments = request_data.get("doctorComments", "")

    payload = consultia_to_medberos_payload(form, doctor_comments)
    result = await medberos_client.predict_diagnoses(payload)

    diagnosticos = []
    if "error" not in result:
        predictions = result.get("predictions", [])
        diagnosticos = medberos_diagnoses_to_consultia(predictions)

    return JSONResponse({
        "success": True,
        "diagnosticos": diagnosticos,
        "examenes": [],
        "tratamientos": [],
    })


@app.post("/medberos/predict-diagnoses")
async def predict_diagnoses_endpoint(request_data: Dict[str, Any]):
    form = request_data.get("form", {})
    doctor_comments = request_data.get("doctorComments", "")

    payload = consultia_to_medberos_payload(form, doctor_comments)
    result = await medberos_client.predict_diagnoses(payload)

    if "error" in result:
        return JSONResponse({"success": False, "error": result["error"]}, status_code=500)

    predictions = result.get("predictions", [])
    diagnosticos = medberos_diagnoses_to_consultia(predictions)

    return JSONResponse({
        "success": True,
        "diagnosticos": diagnosticos,
        "raw": result,
    })


@app.post("/medberos/predict-exams")
async def predict_exams_endpoint(request_data: Dict[str, Any]):
    form = request_data.get("form", {})
    doctor_comments = request_data.get("doctorComments", "")

    payload = consultia_to_medberos_payload(form, doctor_comments)
    result = await medberos_client.predict_exams(payload)

    if "error" in result:
        return JSONResponse({"success": False, "error": result["error"]}, status_code=500)

    predictions = result.get("predictions", [])
    exams = medberos_exams_to_consultia(predictions)

    return JSONResponse({
        "success": True,
        "examenes": exams,
        "raw": result,
    })


@app.post("/medberos/predict-treatments")
async def predict_treatments_endpoint(request_data: Dict[str, Any]):
    form = request_data.get("form", {})
    doctor_comments = request_data.get("doctorComments", "")

    payload = consultia_to_medberos_payload(form, doctor_comments)
    result = await medberos_client.predict_treatments(payload)

    if "error" in result:
        return JSONResponse({"success": False, "error": result["error"]}, status_code=500)

    predictions = result.get("predictions", [])
    tratamientos = medberos_treatments_to_consultia(predictions)

    return JSONResponse({
        "success": True,
        "tratamientos": tratamientos,
        "raw": result,
    })


# ------------------ Schema validation ------------------

MAX_SCHEMA_PROPERTIES = 100


def validate_tab_schema(schema: Any) -> str | None:
    """Return an error message if the schema is invalid, else None."""
    if not isinstance(schema, dict):
        return "schema must be a dict"
    if not isinstance(schema.get("id"), str) or not schema["id"]:
        return "schema.id is required (string)"
    if not isinstance(schema.get("name"), str) or not schema["name"]:
        return "schema.name is required (string)"
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        return "schema.properties is required (non-empty dict)"
    if len(props) > MAX_SCHEMA_PROPERTIES:
        return f"schema.properties exceeds max of {MAX_SCHEMA_PROPERTIES}"
    for key, prop in props.items():
        if not isinstance(prop, dict):
            return f"schema.properties.{key} must be a dict"
        if "type" not in prop:
            return f"schema.properties.{key} missing 'type'"
        if "description" not in prop:
            return f"schema.properties.{key} missing 'description'"
    return None


# ------------------ WebSocket ------------------


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = ws.query_params.get("session") or "default"
    schema_id = ws.query_params.get("schema") or DEFAULT_SCHEMA
    state = session_manager.get_or_create(session_id, schema_id)

    try:
        while True:
            msg = await ws.receive_json()
            logger.info(f"[WS] recv: {msg}")
            typ = msg.get("type")
            text = (msg.get("text") or "").strip()

            if typ == "partial":
                state["partial"] = text

            elif typ == "set_schema":
                schema = msg.get("schema")
                if not schema:
                    await ws.send_json({"type": "error", "message": "set_schema: missing schema"})
                    continue
                err = validate_tab_schema(schema)
                if err:
                    await ws.send_json({"type": "error", "message": f"set_schema: {err}"})
                    continue
                session_manager.set_active_schema(session_id, schema)
                logger.info(f"[WS] set_schema session={session_id} schema_id={schema.get('id')}")
                await ws.send_json({"type": "schema_accepted", "schema_id": schema["id"]})
                # Do NOT re-extract old transcript for the new schema.
                # The offset was set in set_active_schema; only new speech will be extracted.

            elif typ == "final":
                if text:
                    sep = "" if state["final"].endswith((" ", "\n", ".")) else " "
                    state["final"] = (state["final"] + sep + text + ". ").strip()
                    logger.info(f"[WS] final+= session={session_id} chunk_len={len(text)} total_chars={len(state['final'])}")

                    try:
                        current_form = state.get("json_state", {})
                        asyncio.create_task(stream_summary(ws, state["final"], current_form))
                    except Exception as e:
                        logger.exception("[WS] stream_summary error")
                        await ws.send_json({"type": "error", "message": f"Stream error: {e}"})

                    new_fragment = text
                    asyncio.create_task(
                        _run_incremental_update(
                            ws,
                            session_id,
                            schema_id,
                            new_fragment,
                            state.get("json_state", {}),
                            state["final"],
                        )
                    )

                    # Also run tab extraction if a dynamic schema is active
                    if state.get("active_schema"):
                        asyncio.create_task(_run_tab_extraction(ws, session_id))

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _run_incremental_update(
    ws: WebSocket,
    session_id: str,
    schema_id: str,
    fragment: str,
    prev_form: dict,
    transcript: str,
):
    """Orchestration: extract delta, merge, compute missing, generate suggestions, explain."""
    try:
        state = session_manager.get(session_id)
        delta = await extract_form_delta(prev_form, fragment, state["messages"] if state else [])
        updated_form = deep_merge(prev_form, delta)
        missing = compute_missing(updated_form, schema_id)

        suggestions = await generate_contextual_suggestions(
            transcript=transcript,
            current_form=updated_form,
            recent_fragment=fragment,
            schema_id=schema_id,
        )

        await ws.send_json({
            "type": "form_update",
            "form": updated_form,
            "missing": missing,
            "suggestions": suggestions,
        })

        deltas = compute_deltas(prev_form, updated_form)
        if deltas:
            explained = await explain_deltas(transcript, deltas)
            await ws.send_json({"type": "form_delta", "changes": explained})

        session_manager.update_state(session_id, updated_form)

    except Exception as e:
        logger.exception("[WS] incremental update error")
        await ws.send_json({"type": "error", "message": f"Update error: {e}"})


async def _run_tab_extraction(ws: WebSocket, session_id: str):
    """Extract flat key-value fields using the active dynamic schema.
    Only processes transcript text that arrived AFTER the current schema was set,
    so switching tabs doesn't re-map old dictation into the new schema.
    """
    try:
        state = session_manager.get(session_id)
        if not state:
            return
        schema = state.get("active_schema")
        full_transcript = state.get("final", "")
        if not schema or not full_transcript:
            return

        # Only extract from text dictated after this schema was activated
        offset = state.get("schema_transcript_offset", 0)
        transcript = full_transcript[offset:]
        if not transcript.strip():
            return

        fields = await extract_tab_fields(transcript, schema)
        await ws.send_json({
            "type": "tab_fields",
            "schema_id": schema.get("id"),
            "fields": fields,
        })
        logger.info(f"[WS] tab_fields session={session_id} schema={schema.get('id')} keys={len(fields)}")

    except Exception as e:
        logger.exception("[WS] tab extraction error")
        await ws.send_json({"type": "error", "message": f"Tab extraction error: {e}"})


# ------------------ Static files & main ------------------

if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
