# 🐛 DEBUG - PROBLEMAS IDENTIFICADOS

## ❌ PROBLEMAS REPORTADOS

### 1. **El asistente IA no genera resumen inicial**
- No aparece ningún texto en el panel del asistente
- No hay streaming de tokens

### 2. **Motivo de consulta no se detecta**
- Campo "motivoConsulta" permanece vacío
- Es un campo REQUERIDO (1/4)

### 3. **Diagnósticos y tratamientos no se capturan bien**
- Arrays vacíos o con datos incorrectos

### 4. **Lenguaje muy técnico requerido**
- El sistema solo entiende términos médicos exactos
- En consultas reales se usa lenguaje más natural

---

## 🔍 DIAGNÓSTICO PASO A PASO

### PASO 1: Verificar que el WebSocket funciona

**Abrir consola del navegador (F12) y buscar:**

```javascript
[AI WS <<] // Debe haber mensajes
```

Si NO hay mensajes → El WebSocket no está conectado

**Solución:**
1. Verificar que el backend esté corriendo en puerto 8001
2. Verificar que el frontend apunte a ws://127.0.0.1:8001

---

### PASO 2: Verificar que llegan transcripciones

**En la consola del navegador, buscar:**

```javascript
{"type": "final", "text": "..."}
```

Si NO hay → El micrófono no está funcionando

**Solución:**
1. Permitir acceso al micrófono en el navegador
2. Verificar que el servicio STT esté funcionando

---

### PASO 3: Verificar que el backend recibe el texto

**En la terminal del backend (Python), buscar:**

```python
[WS] recv: {'type': 'final', 'text': '...'}
[WS] final+= session=... chunk_len=... total_chars=...
```

Si NO hay → El frontend no está enviando al backend

---

### PASO 4: Verificar que se llama stream_summary()

**En la terminal del backend, buscar:**

```python
[AI] stream_summary ENTER len=... missing=[...]
[AI] assistant_reset SENT
```

Si NO hay → La función no se está ejecutando

**Posibles causas:**
1. Error antes de llegar a esa línea
2. Excepción capturada silenciosamente
3. El texto está vacío

---

### PASO 5: Verificar llamada a OpenAI

**Buscar en logs del backend:**

```python
# Si hay error de OpenAI, debe aparecer
openai.AuthenticationError
openai.RateLimitError
```

**Verificar API Key:**
```bash
# En consultia/backend/.env
OPENAI_API_KEY=sk-proj-...
```

¿La API key es válida? ¿Tiene créditos?

---

## 🔧 SOLUCIONES PROPUESTAS

### SOLUCIÓN 1: Mejorar detección de "Motivo de consulta"

**Problema:** El campo requiere ser muy específico.

**Mejora en el schema (constants.py):**

```python
"motivoConsulta": {
    "type": "string",
    "description": (
        "Razón principal por la cual el paciente consulta. "
        "Puede expresarse de múltiples formas: "
        "- 'acude por...', 'viene por...', 'consulta por...' "
        "- 'refiere...', 'presenta...', 'tiene...' "
        "- Cualquier síntoma o queja principal mencionada al inicio. "
        "Extraer la esencia de por qué viene el paciente. "
        "Ejemplos: 'fiebre', 'dolor abdominal', 'tos persistente', 'control de presión'."
    )
}
```

---

### SOLUCIÓN 2: Mejorar detección de diagnósticos

**Problema:** Solo detecta si dices "diagnóstico:" explícitamente.

**Mejora:**

```python
"diagnosticos": {
    "type": "array",
    "description": (
        "Diagnósticos clínicos del paciente. "
        "Detectar cuando el médico menciona condiciones, enfermedades o impresiones diagnósticas. "
        "Frases clave: 'diagnóstico:', 'impresión:', 'probable:', 'sospecha de:', 'cuadro de:', "
        "'se trata de:', 'compatible con:', 'presenta:' seguido de una condición médica."
    ),
    "items": {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre de la enfermedad o condición (puede ser técnico o coloquial)"
            },
            "tipo": {
                "type": "string",
                "enum": ["presuntivo", "definitivo"],
                "description": (
                    "Tipo de diagnóstico. Si no se especifica, asumir 'presuntivo'. "
                    "Palabras clave: 'presuntivo'/'probable'/'sospecha' vs 'definitivo'/'confirmado'"
                )
            },
            "cie10": {
                "type": "string",
                "description": "Código CIE-10. Solo llenar si se menciona explícitamente."
            }
        }
    }
}
```

---

### SOLUCIÓN 3: Mejorar detección de tratamientos

**Problema:** Solo detecta si dices "tratamiento:" explícitamente.

**Mejora:**

```python
"tratamientos": {
    "type": "array",
    "description": (
        "Tratamientos indicados al paciente. "
        "Detectar medicamentos, procedimientos o indicaciones terapéuticas. "
        "Frases clave: 'tratamiento:', 'plan:', 'indicar:', 'prescribir:', 'dar:', "
        "'tomar:', 'administrar:', 'aplicar:', menciones de nombres de medicamentos, "
        "'continuar con:', 'suspender:', 'iniciar:'. "
        "También detectar dosis mencionadas (mg, ml, cada X horas, por X días)."
    ),
    "items": {
        "type": "object",
        "properties": {
            "medicamento": {
                "type": "string",
                "description": (
                    "Nombre del medicamento, procedimiento o indicación. "
                    "Puede ser nombre comercial, genérico o descripción (ej: 'analgésicos', 'reposo')."
                )
            },
            "dosisIndicacion": {
                "type": "string",
                "description": (
                    "Dosis, frecuencia y duración. "
                    "Detectar patrones: 'X mg/ml cada Y horas por Z días', "
                    "'una tableta', 'dos veces al día', etc."
                )
            }
        }
    }
}
```

---

### SOLUCIÓN 4: Agregar ejemplos al prompt de extracción

**Mejorar extract_form_delta() para dar ejemplos:**

```python
sys = (
    "Eres un asistente que actualiza un objeto JSON de acuerdo a un schema dado.\n\n"

    "IMPORTANTE: Debes interpretar el lenguaje NATURAL del médico, no solo términos técnicos exactos.\n\n"

    "EJEMPLOS DE INTERPRETACIÓN:\n"
    "- 'paciente viene por fiebre' → motivoConsulta: 'fiebre'\n"
    "- 'presenta tos y dolor de cabeza' → sintomasPrincipales: ['tos', 'dolor de cabeza']\n"
    "- 'parece ser una gripe' → diagnosticos: [{nombre: 'gripe', tipo: 'presuntivo'}]\n"
    "- 'le voy a dar paracetamol' → tratamientos: [{medicamento: 'paracetamol'}]\n"
    "- 'que tome una pastilla cada 8 horas' → dosisIndicacion: 'una pastilla cada 8 horas'\n\n"

    "Entradas:\n"
    "  • El estado actual del objeto JSON.\n"
    "  • Un fragmento de texto en lenguaje natural.\n"
    "  • El JSON Schema completo, con descripciones de cada campo.\n\n"

    "Instrucciones:\n"
    "1. Interpreta el SENTIDO del texto, no busques palabras clave exactas.\n"
    "2. Devuelve SOLO un objeto JSON parcial con los campos que deben actualizarse.\n"
    "3. Si no hay información nueva, devuelve {}.\n"
    "4. Usa únicamente claves y estructuras que existan en el schema.\n"
    "5. Lee las descripciones del schema para decidir el campo más adecuado.\n"
    "6. Respeta los tipos de datos definidos en el schema.\n"
    "7. Para arrays, agrega elementos en una lista.\n"
)
```

---

## 🧪 PRUEBA DE DEBUG

### Test 1: Verificar API Key

```bash
# En terminal (Windows):
cd consultia\backend
.venv\Scripts\activate
python

>>> import os
>>> from dotenv import load_dotenv
>>> load_dotenv()
>>> print(os.getenv("OPENAI_API_KEY"))
# Debe mostrar: sk-proj-...
```

Si aparece `None` → El archivo .env no se está leyendo

---

### Test 2: Probar OpenAI directamente

```python
from openai import OpenAI

client = OpenAI(api_key="tu_api_key_aqui")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Di hola"}
    ]
)

print(response.choices[0].message.content)
# Debe responder algo
```

Si falla → Problema con OpenAI (API key, créditos, conexión)

---

### Test 3: Hablar de forma natural

Prueba con estos ejemplos más naturales:

```
❌ TÉCNICO (puede no funcionar):
"Motivo de consulta es cefalea tensional"

✅ NATURAL (debería funcionar después de la mejora):
"Paciente viene por dolor de cabeza"
```

```
❌ TÉCNICO:
"Diagnóstico presuntivo faringitis aguda código CIE J02.9"

✅ NATURAL:
"Parece que tiene la garganta inflamada, probablemente una faringitis"
```

```
❌ TÉCNICO:
"Tratamiento paracetamol 500mg cada 8 horas vía oral"

✅ NATURAL:
"Le voy a dar paracetamol, que tome una pastilla cada 8 horas"
```

---

## 📋 CHECKLIST DE VERIFICACIÓN

Marca cada punto mientras debugueas:

### Backend:
- [ ] El servidor está corriendo en puerto 8001
- [ ] El archivo .env existe y tiene OPENAI_API_KEY válida
- [ ] Los logs muestran `[WS] recv: ...`
- [ ] Los logs muestran `[AI] stream_summary ENTER...`
- [ ] No hay errores de OpenAI en los logs

### Frontend:
- [ ] El navegador tiene acceso al micrófono
- [ ] La consola muestra mensajes WebSocket
- [ ] Los mensajes `{type: "final", text: "..."}` se envían
- [ ] Llegan mensajes `{type: "assistant_token", delta: "..."}`
- [ ] Llegan mensajes `{type: "form_update", form: {...}}`

### Flujo completo:
- [ ] Al hablar, el texto se transcribe (se ve en pantalla)
- [ ] El asistente IA genera texto
- [ ] Los campos del formulario se llenan
- [ ] El progreso aumenta

---

## 🚨 ERRORES COMUNES

### Error: "Invalid API key"

```
openai.AuthenticationError: Error code: 401
```

**Solución:**
1. Verifica que la API key sea correcta en .env
2. Regenera la API key en https://platform.openai.com/api-keys
3. Verifica que no tenga espacios extra

---

### Error: "Rate limit exceeded"

```
openai.RateLimitError: Error code: 429
```

**Solución:**
1. Verifica que tu cuenta de OpenAI tenga créditos
2. Espera unos minutos si has hecho muchas llamadas
3. Considera usar un tier de pago

---

### Error: WebSocket connection failed

```
WebSocket connection to 'ws://...' failed
```

**Solución:**
1. Verifica que el backend esté corriendo
2. Verifica la URL en environment.ts
3. Revisa CORS en server.py

---

## 📝 PRÓXIMOS PASOS

1. **Primero:** Ejecuta el proyecto y revisa los logs
2. **Anota:** Qué errores aparecen en backend y frontend
3. **Comparte:** Los mensajes de error específicos
4. **Después:** Implementaremos las soluciones

---

¿Quieres que te ayude a debuggear en vivo?
Comparte los logs de la terminal del backend cuando hables en el micrófono.
