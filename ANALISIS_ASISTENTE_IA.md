# 🔍 ANÁLISIS: ¿El Asistente IA lee TODO el contexto?

## ✅ LO QUE SÍ ESTÁ FUNCIONANDO

### 1. **El asistente IA SÍ lee todo el transcript acumulado**

**Código:** [server.py:285](c:\Trabajo\Clinica\Medberos\NewMed\consultia\backend\server.py#L285)
```python
asyncio.create_task(stream_summary(ws, state["final"]))
```

- ✅ `state["final"]` contiene **TODO** el texto transcrito desde el inicio
- ✅ Se acumula con cada mensaje `"final"` que llega
- ✅ La IA ve TODO el contexto conversacional

**Ejemplo:**
```python
# Primera transcripción
state["final"] = "Paciente con fiebre."

# Segunda transcripción
state["final"] = "Paciente con fiebre. Tiene tos seca."

# La IA siempre recibe el texto completo acumulado
```

---

## ❌ LO QUE NO ESTÁ FUNCIONANDO

### 1. **El asistente IA NO recibe información sobre campos faltantes**

**Código actual:** [server.py:100-129](c:\Trabajo\Clinica\Medberos\NewMed\consultia\backend\server.py#L100-L129)

```python
async def stream_summary(ws: WebSocket, transcript: str):
    system = (
        "Eres un asistente clínico. Resume en 2–4 líneas lo más relevante del caso: "
        "motivo de consulta, síntomas clave, hallazgos, y si falta información para la historia clínica. "
        "No inventes datos y mantén tono profesional."
    )

    stream = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": transcript}  # ❌ SOLO recibe transcript
        ],
        temperature=0.2,
        stream=True
    )
```

**Problema:**
- ❌ NO recibe `missing` (campos faltantes)
- ❌ NO recibe `suggestions` (sugerencias)
- ❌ NO recibe el estado actual del formulario

**Resultado:**
El asistente IA genera un resumen general, pero **NO menciona** qué campos faltan ni qué información se necesita.

---

### 2. **Las sugerencias se envían al frontend pero NO a la IA**

**Flujo actual:**

```
Backend calcula → missing = ["diagnosticos", "tratamientos"]
               ↓
Backend genera → suggestions = ["Registre al menos un diagnóstico..."]
               ↓
Backend envía al frontend → {"type": "form_update", "suggestions": [...]}
               ↓
Frontend muestra sugerencias en UI ✅
               ↓
IA NO las ve ❌
```

**Por qué:**
La función `stream_summary()` se ejecuta **ANTES** de calcular `missing` y `suggestions`:

```python
# PASO 1: Se genera el resumen (NO tiene missing/suggestions aún)
asyncio.create_task(stream_summary(ws, state["final"]))

# PASO 2: Se extrae el formulario y se calculan missing/suggestions
asyncio.create_task(run_incremental_update(...))
```

---

## 🎯 CÓMO VERIFICAR EL PROBLEMA

### Prueba 1: Di solo esto
```
"Paciente con fiebre"
```

**Resultado esperado actual:**
- ✅ Asistente IA: "Paciente refiere fiebre. Se requiere más información..."
- ✅ Campos faltantes: ["Motivo de consulta", "Síntomas principales", "diagnósticos", "tratamientos"]
- ✅ Sugerencias: Aparecen en la UI

**Problema:**
- ❌ El asistente IA NO dice explícitamente "Falta registrar diagnósticos y tratamientos"

### Prueba 2: Completa motivo y síntomas
```
"Paciente acude por fiebre. Síntomas principales: fiebre, tos, dolor de garganta."
```

**Resultado esperado mejorado:**
- ✅ Asistente IA debería decir: "Paciente con síntomas respiratorios. **Pendiente: diagnósticos y plan de tratamiento.**"
- Pero actualmente NO lo hace ❌

---

## 🔧 SOLUCIONES PROPUESTAS

### Opción 1: Modificar `stream_summary()` para recibir contexto adicional

**Cambio en [server.py:100](c:\Trabajo\Clinica\Medberos\NewMed\consultia\backend\server.py#L100):**

```python
async def stream_summary(
    ws: WebSocket,
    transcript: str,
    missing: List[str] = [],      # ← NUEVO
    suggestions: List[str] = []   # ← NUEVO
):
    # Construir contexto enriquecido
    context_parts = [transcript]

    if missing:
        missing_str = ", ".join(missing)
        context_parts.append(f"\n\nCAMPOS FALTANTES: {missing_str}")

    if suggestions:
        sugg_str = "\n".join(f"- {s}" for s in suggestions)
        context_parts.append(f"\n\nSUGERENCIAS PARA COMPLETAR:\n{sugg_str}")

    full_context = "\n".join(context_parts)

    system = (
        "Eres un asistente clínico. Resume en 2–4 líneas lo más relevante del caso. "
        "Si hay campos faltantes, menciónalos brevemente al final. "
        "Mantén tono profesional y útil."
    )

    stream = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": full_context}  # ← Contexto enriquecido
        ],
        temperature=0.2,
        stream=True
    )
```

**Resultado esperado:**
```
Asistente IA: "Paciente con cuadro febril y síntomas respiratorios.
Presión arterial normal. Pendiente: registrar diagnósticos y plan de tratamiento."
```

---

### Opción 2: Invocar `stream_summary()` DESPUÉS de calcular missing/suggestions

**Cambio en [server.py:283-302](c:\Trabajo\Clinica\Medberos\NewMed\consultia\backend\server.py#L283-L302):**

**ANTES (actual):**
```python
# 1) Streaming de asistente
asyncio.create_task(stream_summary(ws, state["final"]))

# 2) Form extraction
asyncio.create_task(run_incremental_update(...))
```

**DESPUÉS (mejorado):**
```python
# 1) Primero extraer formulario y calcular missing/suggestions
await run_incremental_update_sync(...)  # Versión síncrona

# 2) Luego generar resumen con contexto completo
missing = state.get("missing", [])
suggestions = state.get("suggestions", [])
asyncio.create_task(stream_summary(ws, state["final"], missing, suggestions))
```

**Ventaja:**
- El asistente IA tiene acceso a la información más actualizada
- Puede guiar al médico sobre qué falta

**Desventaja:**
- El resumen tarda un poco más en aparecer (debe esperar extracción de formulario)

---

### Opción 3: Sistema de 2 fases (Resumen rápido + Análisis detallado)

**Fase 1: Resumen inmediato (actual)**
```
"Paciente con fiebre y síntomas respiratorios."
```

**Fase 2: Análisis después de form_update**
```
"Análisis de completitud: ✅ Síntomas registrados.
⚠️ Pendiente: diagnósticos y tratamientos."
```

**Implementación:**
- Mantener `stream_summary()` como está (rápido)
- Agregar una nueva función `stream_completeness_check()` que se llame al final de `run_incremental_update()`

---

## 📊 COMPARACIÓN DE OPCIONES

| Opción | Velocidad | Precisión | Complejidad |
|--------|-----------|-----------|-------------|
| **Opción 1** | ⚡ Rápida | ⭐⭐⭐ Alta | 🔧 Media |
| **Opción 2** | 🐢 Lenta | ⭐⭐⭐⭐ Muy Alta | 🔧 Media |
| **Opción 3** | ⚡⚡ Muy rápida | ⭐⭐⭐⭐⭐ Excelente | 🔧🔧 Alta |

**Recomendación:** **Opción 3** (sistema de 2 fases) para mejor UX.

---

## 🎯 IMPLEMENTACIÓN RECOMENDADA

### Modificación mínima (Opción 1 simplificada)

**Archivo:** `consultia/backend/server.py`

**Cambio en línea 100:**
```python
async def stream_summary(ws: WebSocket, transcript: str, current_form: dict = {}):
    # Calcular campos faltantes in-situ
    missing = compute_missing(current_form)

    # Construir prompt contextualizado
    system = (
        "Eres un asistente clínico. Resume en 2–4 líneas lo más relevante del caso: "
        "motivo de consulta, síntomas clave, hallazgos. "
        "Si identificas información faltante importante, menciónala brevemente. "
        "Mantén tono profesional."
    )

    user_prompt = transcript
    if missing:
        missing_friendly = []
        map_friendly = {
            "afiliacion.motivoConsulta": "motivo de consulta",
            "anamnesis.sintomasPrincipales": "síntomas principales",
            "diagnosticos": "diagnósticos",
            "tratamientos": "plan de tratamiento"
        }
        for m in missing:
            missing_friendly.append(map_friendly.get(m, m))

        user_prompt += f"\n\n[NOTA: Campos pendientes de registro: {', '.join(missing_friendly)}]"

    stream = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        stream=True
    )
    # ... resto del código igual
```

**Cambio en línea 285:**
```python
asyncio.create_task(stream_summary(ws, state["final"], state.get("json_state", {})))
```

**Resultado esperado:**
```
Asistente IA: "Paciente con cuadro febril y sintomatología respiratoria.
Se registraron síntomas principales. Pendiente de completar: diagnósticos
y plan de tratamiento."
```

---

## ✅ RESUMEN FINAL

### Estado actual:
- ✅ El asistente IA lee todo el transcript
- ❌ NO lee campos faltantes
- ❌ NO lee sugerencias
- ❌ NO puede guiar al médico activamente

### Con la mejora propuesta:
- ✅ El asistente IA lee todo el transcript
- ✅ Lee campos faltantes
- ✅ Puede mencionar qué falta
- ✅ Guía activamente al médico

---

¿Quieres que implemente alguna de estas opciones?
