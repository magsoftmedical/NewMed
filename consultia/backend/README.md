# Consult-IA Backend

FastAPI backend for Consult-IA. Receives voice-to-text from the frontend via WebSocket, processes it through OpenAI to extract structured clinical data in real time, and returns form updates, AI summaries, and contextual suggestions.

## Project Structure

```
backend/
├── server.py                       # FastAPI app — thin routes & WebSocket handler
├── config.py                       # OpenAI client, env vars, logger (shared singleton)
├── sessions.py                     # SessionManager — per-session state with schema awareness
├── constants.py                    # Backward-compat re-exports (SCHEMA, REQUIRED_KEYS)
│
├── schemas/
│   ├── registry.py                 # list_schemas(), get_schema(), get_json_schema(), get_required_keys()
│   └── definitions/
│       └── historia_clinica.json   # Schema definition (JSON Schema + required keys)
│
├── services/
│   ├── form_extraction.py          # OpenAI extraction: delta, merge, deltas, explain, stream summary
│   ├── suggestions.py              # Missing field detection + AI-generated contextual suggestions
│   ├── transcription.py            # Whisper transcription + hallucination filtering
│   └── document.py                 # PDF/image → Vision API → structured JSON
│
├── integrations/
│   └── medberos/
│       ├── __init__.py             # Re-exports client & mapper functions
│       ├── client.py               # MedberosClient — async HTTP client for Medberos AI API
│       ├── mapper.py               # Bidirectional format conversion (Consult-IA <-> Medberos)
│       └── examples.json           # API request/response examples (reference)
│
├── tests/
│   ├── test_medberos.py            # Standalone integration test for Medberos API
│   ├── test_openai.py              # Standalone OpenAI connectivity test
│   └── test_simple.py              # Minimal streaming test
│
├── requirements.txt
├── Dockerfile
└── Procfile
```

## Import Dependency Graph

No circular imports. Each layer only imports from layers above it:

```
config.py
  └── schemas/registry.py
        └── sessions.py
              └── services/*
                    └── server.py
```

`integrations/medberos/` is independent — only imported by `server.py`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check (basic) |
| `GET` | `/health` | Health check with model info |
| `GET` | `/schemas` | List available form schemas |
| `POST` | `/transcribe` | Whisper audio transcription |
| `POST` | `/extract-document` | Extract structured data from image/PDF |
| `WS` | `/ws?session=ID&schema=historia_clinica` | Real-time voice → form extraction |
| `GET` | `/medberos/test` | Test Medberos API connection |
| `POST` | `/medberos/predict-all` | Predict diagnoses, exams, treatments |
| `POST` | `/medberos/predict-diagnoses` | Predict diagnoses only |
| `POST` | `/medberos/predict-exams` | Predict exams only |
| `POST` | `/medberos/predict-treatments` | Predict treatments only |

## WebSocket Message Types

**Client → Server:**
- `{"type": "partial", "text": "..."}` — interim speech recognition result
- `{"type": "final", "text": "..."}` — confirmed speech recognition result

**Server → Client:**
- `{"type": "assistant_reset"}` — clear previous AI summary
- `{"type": "assistant_token", "delta": "..."}` — AI narrative summary (streamed)
- `{"type": "form_update", "form": {...}, "missing": [...], "suggestions": [...]}` — updated form state
- `{"type": "form_delta", "changes": [...]}` — explained field changes with evidence
- `{"type": "error", "message": "..."}` — error notification

## Schema Registry

Schemas live as JSON files in `schemas/definitions/`. Each file bundles:
- `id` — unique identifier (used in API params)
- `name` — display name
- `required_keys` — dot-paths for minimum required fields
- `schema` — full JSON Schema for the form

**Adding a new schema:** drop a `.json` file in `schemas/definitions/`. No code changes needed.

## Setup

```bash
# Create and activate environment
conda activate consult-ia

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # then fill in OPENAI_API_KEY

# Run (development)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key |
| `OPENAI_MODEL_TEXT` | `gpt-4o-mini` | Model for streaming summaries |
| `OPENAI_MODEL_JSON` | `gpt-4o-mini` | Model for structured JSON extraction |
| `ALLOWED_ORIGINS` | `http://localhost:4200,...` | CORS origins (comma-separated) |
| `MEDBEROS_API_URL` | `https://test-api.medberos.com/api` | Medberos AI API base URL |
| `MEDBEROS_API_KEY` | — | Medberos API key |
| `MEDBEROS_API_SECRET` | — | Medberos API secret |
| `PORT` | `8001` | Server port (used by `python server.py`) |

## Running Tests

Tests are standalone scripts (not pytest):

```bash
cd backend
python tests/test_openai.py      # verify OpenAI connection
python tests/test_medberos.py    # verify Medberos integration
python tests/test_simple.py      # minimal streaming test
```

## Docker

```bash
docker build -t consultia-backend .
docker run -p 5000:5000 --env-file .env consultia-backend
```
