# ✅ ASISTENTE IA MEJORADO - GUÍA DE PRUEBA

## 🎯 CAMBIOS IMPLEMENTADOS

### ✨ Mejoras realizadas:

1. **El asistente IA ahora recibe el estado del formulario**
   - Antes: Solo veía el transcript
   - Ahora: Ve el transcript + campos faltantes

2. **Prompt mejorado con instrucciones claras**
   - Instrucción específica para mencionar información faltante
   - Tono más profesional y orientado a guiar al médico

3. **Logging mejorado**
   - Se registran los campos faltantes en cada actualización
   - Útil para depuración

---

## 🧪 PRUEBAS A REALIZAR

### **PRUEBA 1: Inicio de consulta (Solo motivo)**

**Di esto:**
```
"Paciente acude por fiebre alta"
```

**Resultado ANTES (antiguo):**
```
Asistente IA: "Paciente refiere fiebre alta."
```

**Resultado AHORA (mejorado):**
```
Asistente IA: "Paciente refiere fiebre alta.
Pendiente: síntomas principales, diagnósticos, plan de tratamiento."
```

**Campos faltantes esperados:**
- anamnesis.sintomasPrincipales
- diagnosticos
- tratamientos

---

### **PRUEBA 2: Agregar síntomas**

**Di esto:**
```
"Los síntomas principales son fiebre, tos seca y dolor de garganta"
```

**Resultado esperado:**
```
Asistente IA: "Paciente con cuadro febril, tos seca y odinofagia.
Pendiente: diagnósticos, plan de tratamiento."
```

**Campos faltantes esperados:**
- diagnosticos
- tratamientos

**Progreso:** 2/4 (50%)

---

### **PRUEBA 3: Agregar examen físico y diagnóstico**

**Di esto:**
```
"Presión arterial 120/80, temperatura 38.5 grados.
Diagnóstico: faringitis aguda, presuntivo"
```

**Resultado esperado:**
```
Asistente IA: "Paciente con cuadro febril y síntomas respiratorios.
Signos vitales: PA 120/80, temperatura 38.5°C.
Diagnóstico: faringitis aguda. Pendiente: plan de tratamiento."
```

**Campos faltantes esperados:**
- tratamientos

**Progreso:** 3/4 (75%)

---

### **PRUEBA 4: Completar con tratamiento**

**Di esto:**
```
"Tratamiento: paracetamol 500mg cada 8 horas"
```

**Resultado esperado:**
```
Asistente IA: "Paciente con faringitis aguda y cuadro febril.
Signos vitales estables salvo temperatura elevada.
Tratamiento: paracetamol 500mg cada 8 horas."
```

**Campos faltantes esperados:**
- Ninguno ✅

**Progreso:** 4/4 (100%)

**IMPORTANTE:** Al estar completo, el asistente NO debe mencionar pendientes.

---

## 📊 COMPARACIÓN ANTES vs AHORA

### Escenario: Paciente con solo motivo de consulta

| Aspecto | ANTES | AHORA |
|---------|-------|-------|
| **Input** | "Paciente con fiebre" | "Paciente con fiebre" |
| **Contexto IA** | Solo transcript | Transcript + missing fields |
| **Output** | "Paciente refiere fiebre." | "Paciente refiere fiebre. Pendiente: síntomas principales, diagnósticos, plan de tratamiento." |
| **Utilidad** | ⭐⭐ Informativo | ⭐⭐⭐⭐⭐ Guía activa |

---

## 🔍 CÓMO VERIFICAR QUE FUNCIONA

### 1. **Revisar logs del backend**

Abre la terminal donde corre el backend y busca:

```
[AI] stream_summary ENTER len=25, missing=['anamnesis.sintomasPrincipales', 'diagnosticos', 'tratamientos']
```

Esto confirma que la función recibe los campos faltantes.

### 2. **Observar el panel del asistente en la UI**

Debe mostrar mensajes como:
- "Pendiente: diagnósticos, plan de tratamiento"
- "Se requiere: síntomas principales"
- Al completar todo: NO menciona pendientes

### 3. **Verificar en la consola del navegador**

Abre F12 → Console y busca:
```
[AI WS <<] {"type": "assistant_token", "delta": "Pendiente"}
```

---

## 🎬 GUION DE PRUEBA RÁPIDO (2 minutos)

Lee esto en orden, pausando 5 segundos entre cada línea:

```
1. "Paciente María Rodríguez, treinta años, femenino"
   → Espera 5s → Observa asistente

2. "Acude por fiebre alta desde hace tres días"
   → Espera 5s → ¿Menciona campos faltantes?

3. "Síntomas principales: fiebre, tos seca, dolor de cabeza"
   → Espera 5s → ¿Actualizó la lista de pendientes?

4. "Presión arterial 120 sobre 80, temperatura 38 punto 5"
   → Espera 5s

5. "Diagnóstico presuntivo: faringitis aguda"
   → Espera 5s → ¿Solo falta tratamiento?

6. "Tratamiento: paracetamol 500 miligramos cada 8 horas"
   → Espera 5s → ¿Ya NO menciona pendientes?
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

Marca cada punto después de probarlo:

- [ ] El asistente menciona campos faltantes al inicio
- [ ] La lista de pendientes se actualiza conforme hablas
- [ ] Al completar los 4 campos requeridos, NO menciona pendientes
- [ ] El resumen es coherente y profesional
- [ ] Los logs del backend muestran `missing=[...]`
- [ ] El progreso cambia de 0/4 → 1/4 → 2/4 → 3/4 → 4/4

---

## 🐛 TROUBLESHOOTING

### ❌ "El asistente NO menciona campos faltantes"

**Posibles causas:**
1. El backend no se reinició después del cambio
2. Hay un error en la función `compute_missing()`
3. El formulario ya está completo (verifica que falten campos)

**Solución:**
1. Detén el backend (Ctrl+C en la terminal)
2. Vuelve a ejecutar: `uvicorn server:app --host 0.0.0.0 --port 8001 --reload`
3. Recarga la página del frontend (F5)
4. Prueba de nuevo

---

### ❌ "El asistente siempre dice que falta todo"

**Causa:** Los campos no se están llenando correctamente.

**Solución:**
1. Abre F12 → Network → WS
2. Verifica mensajes `{"type": "form_update", "form": {...}}`
3. Revisa que el formulario contenga los datos que dictaste
4. Si está vacío, el problema es en `extract_form_delta()`

---

### ❌ "Error en el backend: 'NoneType' object..."

**Causa:** El formulario es `None` o no tiene la estructura esperada.

**Solución:** Ya está manejado con el parámetro por defecto `current_form: dict = None`
y el check `if current_form:`.

Si persiste, revisa el log completo del error.

---

## 📈 MEJORAS FUTURAS OPCIONALES

### 1. **Agregar nivel de criticidad**

Modificar el prompt para diferenciar:
- 🔴 Crítico: diagnósticos, tratamientos
- 🟡 Importante: síntomas principales
- 🟢 Opcional: funciones biológicas, antecedentes

### 2. **Sugerencias específicas**

En lugar de solo decir "Pendiente: diagnósticos", podría decir:
"Sugerencia: Basado en los síntomas, considere registrar un diagnóstico presuntivo."

### 3. **Validación cruzada**

Detectar inconsistencias, por ejemplo:
"Alerta: Se mencionó fiebre de 38.5°C pero no está registrada en signos vitales."

---

## 🚀 SIGUIENTE PASO

1. **Ejecuta el proyecto:**
   ```cmd
   INICIAR_PROYECTO.bat
   ```

2. **Abre el navegador:**
   ```
   http://localhost:4200
   ```

3. **Sigue el guion de prueba rápido de arriba**

4. **Verifica que el asistente mencione los campos faltantes**

---

## 📝 CÓDIGO MODIFICADO

### Archivo: `consultia/backend/server.py`

**Línea 100-166:** Función `stream_summary()` mejorada
- Ahora recibe `current_form` como parámetro
- Calcula `missing` usando `compute_missing()`
- Construye prompt con contexto de campos faltantes
- Mejor logging

**Línea 322-324:** Llamada actualizada
- Pasa `state.get("json_state", {})` a `stream_summary()`

---

¡TODO LISTO! Ahora prueba el sistema mejorado. 🎉
