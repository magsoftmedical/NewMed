# 🎤 GUION DE PRUEBA - CONSULTIA

## 📋 OBJETIVO
Verificar que TODOS los campos se llenan correctamente mediante transcripción de voz y que el asistente IA genera resúmenes coherentes y sugerencias útiles.

---

## 🔴 CAMPOS REQUERIDOS (Verificar que NO estén vacíos al final)
✅ **afiliacion.motivoConsulta**
✅ **anamnesis.sintomasPrincipales**
✅ **diagnosticos** (mínimo 1)
✅ **tratamientos** (mínimo 1)

---

## 🎯 GUION DIVIDIDO EN SECCIONES

### 📝 SECCIÓN 1: DATOS DE AFILIACIÓN (30 segundos)

**DI ESTO:**
```
"Buenos días. Paciente de nombre completo María Elena Rodríguez Torres.
Tiene treinta y cinco años y cuatro meses de edad.
Sexo femenino. DNI número siete seis cinco cuatro tres dos uno ocho.
Grupo sanguíneo A positivo. Fecha de hoy catorce de enero del dos mil veinticinco.
Hora de consulta diez de la mañana.
Seguro es EsSalud. Tipo de consulta ambulatoria.
Número de seguro tres cuatro cinco seis siete ocho nueve.
La paciente acude por fiebre alta y malestar general."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ nombreCompleto: "María Elena Rodríguez Torres"
- ✅ edad: {anios: 35, meses: 4}
- ✅ sexo: "femenino"
- ✅ dni: "76543218"
- ✅ grupoSangre: "A+"
- ✅ fechaHora: "14/01/2025 10:00"
- ✅ seguro: "EsSalud"
- ✅ tipoConsulta: "ambulatoria"
- ✅ numeroSeguro: "3456789"
- ✅ **motivoConsulta: "fiebre alta y malestar general"** ← REQUERIDO

**ESPERA 5 SEGUNDOS** y verifica:
- ¿Se llenó el campo "Motivo de consulta"?
- ¿El asistente IA generó un resumen inicial?

---

### 📝 SECCIÓN 2: ANAMNESIS - SÍNTOMAS Y ENFERMEDAD ACTUAL (45 segundos)

**DI ESTO:**
```
"La paciente refiere que su tiempo de enfermedad es de cinco días.
Los síntomas principales son fiebre, tos seca, dolor de garganta y cefalea.
Relato de la enfermedad: inició hace cinco días con sensación de alza térmica,
temperatura máxima registrada de treinta y nueve grados.
Asociado a tos seca, dolor al tragar y dolor de cabeza frontal.
No ha presentado dificultad respiratoria ni dolor torácico.

Respecto a funciones biológicas: apetito disminuido,
sed conservada, orina de color amarillo claro sin molestias,
deposiciones normales, sueño interrumpido por la tos.

Antecedentes personales: hipertensión arterial controlada con medicación.
Antecedentes del padre: diabetes mellitus tipo dos.
Antecedentes de la madre: hipertensión arterial.
Alergias conocidas: alergia a la penicilina.
Medicamentos actuales: enalapril diez miligramos al día."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ tiempoEnfermedad: "5 días"
- ✅ **sintomasPrincipales: ["fiebre", "tos seca", "dolor de garganta", "cefalea"]** ← REQUERIDO
- ✅ relato: (todo el relato de enfermedad)
- ✅ funcionesBiologicas:
  - apetito: "disminuido"
  - sed: "conservada"
  - orina: "amarillo claro sin molestias"
  - deposiciones: "normales"
  - sueno: "interrumpido por la tos"
- ✅ antecedentes:
  - personales: ["hipertensión arterial controlada"]
  - padre: ["diabetes mellitus tipo 2"]
  - madre: ["hipertensión arterial"]
- ✅ alergias: ["penicilina"]
- ✅ medicamentos: ["enalapril 10mg/día"]

**ESPERA 5 SEGUNDOS** y verifica:
- ¿Se llenaron los síntomas principales como array?
- ¿El asistente IA mencionó los síntomas clave?
- ¿Aparece progreso 2/4 completado?

---

### 📝 SECCIÓN 3: EXAMEN CLÍNICO (60 segundos)

**DI ESTO:**
```
"Al examen físico:
Presión arterial ciento veinte sobre ochenta milímetros de mercurio.
Frecuencia cardíaca ochenta y cinco latidos por minuto.
Frecuencia respiratoria dieciocho respiraciones por minuto.
Temperatura treinta y ocho punto cinco grados centígrados.
Saturación de oxígeno noventa y ocho por ciento.
Peso sesenta y cinco kilogramos. Talla un metro sesenta y cinco centímetros.
Índice de masa corporal veinticuatro.
Escala de Glasgow quince puntos.

Estado general: paciente en regular estado general, hidratada, afebril en este momento.

Descripción por sistemas:
Piel: tibia, hidratada, no se observan lesiones.
Tejido celular subcutáneo: conservado.
Cabeza: normocéfala, sin traumatismos.
Cuello: no adenopatías palpables.
Tórax: simétrico, expansibilidad conservada.
Pulmones: murmullo vesicular pasa bien en ambos campos pulmonares,
no se auscultan ruidos agregados.
Corazón: ruidos cardíacos rítmicos, de buen tono, no soplos.
Abdomen: blando, depresible, no doloroso a la palpación, ruidos hidroaéreos presentes.
Extremidades: sin edema, pulsos periféricos presentes.
Neurológico: paciente orientada en tiempo espacio y persona,
pupilas isocóricas fotorreactivas, fuerza muscular conservada."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ signosVitales:
  - PA: "120/80"
  - FC: 85
  - FR: 18
  - temperatura: 38.5
  - SpO2: 98
  - peso: 65
  - talla: 165
  - IMC: 24
  - glasgow: 15
- ✅ estadoGeneral: "regular estado general, hidratada, afebril"
- ✅ sistemas (todos):
  - piel, tcs, cabeza, cuello, torax, pulmones, corazon, abdomen, extremidades, neurologico

**ESPERA 10 SEGUNDOS** y verifica:
- ¿Se llenaron todos los signos vitales con valores numéricos correctos?
- ¿El asistente IA mencionó los hallazgos del examen físico?

---

### 📝 SECCIÓN 4: DIAGNÓSTICOS (20 segundos)

**DI ESTO:**
```
"Diagnósticos:
Primero, faringitis aguda, diagnóstico presuntivo, código CIE diez J cero dos punto nueve.
Segundo, hipertensión arterial esencial, diagnóstico definitivo, código CIE diez I diez."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ **diagnosticos:** ← REQUERIDO
  - [0]: {nombre: "faringitis aguda", tipo: "presuntivo", cie10: "J02.9"}
  - [1]: {nombre: "hipertensión arterial esencial", tipo: "definitivo", cie10: "I10"}

**ESPERA 5 SEGUNDOS** y verifica:
- ¿Aparecen 2 diagnósticos en el formulario?
- ¿El progreso cambió a 3/4?
- ¿El asistente IA resumió los diagnósticos?

---

### 📝 SECCIÓN 5: TRATAMIENTOS (30 segundos)

**DI ESTO:**
```
"Plan de tratamiento:
Primero, paracetamol quinientos miligramos, tomar una tableta cada ocho horas por cinco días.
Segundo, ibuprofeno cuatrocientos miligramos, tomar una tableta cada doce horas por tres días.
Tercero, abundantes líquidos y reposo relativo.
Cuarto, continuar con enalapril diez miligramos una vez al día.
Control en cinco días o antes si presenta signos de alarma."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ **tratamientos:** ← REQUERIDO
  - [0]: {medicamento: "paracetamol", dosisIndicacion: "500mg cada 8h por 5 días"}
  - [1]: {medicamento: "ibuprofeno", dosisIndicacion: "400mg cada 12h por 3 días"}
  - [2]: {medicamento: "abundantes líquidos", dosisIndicacion: "reposo relativo"}
  - [3]: {medicamento: "enalapril", dosisIndicacion: "10mg una vez al día"}

**ESPERA 5 SEGUNDOS** y verifica:
- ¿Aparecen 4 tratamientos?
- ¿El progreso es 4/4 (100%)?
- ¿Las sugerencias desaparecieron?
- ¿El asistente IA mencionó el plan terapéutico completo?

---

### 📝 SECCIÓN 6: FIRMA (15 segundos)

**DI ESTO:**
```
"Firma del médico tratante: Doctor Juan Carlos Mendoza Pérez.
Número de colegiatura: CMP cincuenta y seis mil setecientos ochenta y nueve.
Fecha de atención: catorce de enero del dos mil veinticinco."
```

**CAMPOS QUE SE DEBEN LLENAR:**
- ✅ firma:
  - medico: "Dr. Juan Carlos Mendoza Pérez"
  - colegiatura: "CMP 56789"
  - fecha: "14/01/2025"

---

## ✅ CHECKLIST DE VERIFICACIÓN

Después de completar todo el guion, verifica lo siguiente:

### 🎯 CAMPOS REQUERIDOS (4/4)
- [ ] **Motivo de consulta** lleno
- [ ] **Síntomas principales** con al menos 1 elemento
- [ ] **Diagnósticos** con al menos 1 elemento
- [ ] **Tratamientos** con al menos 1 elemento

### 📊 PROGRESO
- [ ] Progreso muestra "4/4" o "100%"
- [ ] No hay campos faltantes (missing)
- [ ] No hay sugerencias (suggestions)

### 🤖 ASISTENTE IA
- [ ] Generó resumen inicial con motivo de consulta
- [ ] Actualizó resumen con síntomas
- [ ] Mencionó hallazgos del examen físico
- [ ] Incluyó diagnósticos en el resumen
- [ ] Resumió el plan de tratamiento
- [ ] El resumen es coherente y profesional (2-4 líneas)

### 🔄 DELTAS (CAMBIOS EXPLICADOS)
- [ ] Se muestran los cambios recientes
- [ ] Cada cambio tiene un "reason" (razón)
- [ ] Cada cambio tiene "evidence" (evidencia textual)

### 📝 TODOS LOS CAMPOS
Marca cada sección que se llenó correctamente:
- [ ] Afiliación (9 campos)
- [ ] Anamnesis completa
- [ ] Signos vitales (9 valores)
- [ ] Examen por sistemas
- [ ] Diagnósticos (mínimo 1)
- [ ] Tratamientos (mínimo 1)
- [ ] Firma del médico

---

## 🐛 SI ALGO NO FUNCIONA

### ❌ Si NO se llenan los campos:
1. Abre la consola del navegador (F12)
2. Ve a la pestaña "Network" → "WS" (WebSocket)
3. Verifica que recibes mensajes tipo `form_update`
4. Copia el último mensaje y revísalo

### ❌ Si el asistente IA no se actualiza:
1. Verifica mensajes tipo `assistant_reset` y `assistant_token`
2. Revisa la consola del backend (terminal del servidor Python)
3. Busca logs que digan `[AI] stream_summary ENTER`

### ❌ Si no aparecen sugerencias:
1. Verifica que falten campos requeridos
2. Revisa el mensaje `form_update` → `suggestions`
3. Comprueba que `missing` tenga elementos

---

## 📹 TIPS PARA LA PRUEBA

1. **Habla claramente** y pausadamente
2. **No hables muy rápido**, la IA necesita procesar
3. **Espera 3-5 segundos** entre secciones
4. **Observa el panel del asistente IA** mientras hablas
5. **Revisa los campos del formulario** en tiempo real
6. **Ten la consola del navegador abierta** (F12)

---

## 🎬 VERSIÓN CORTA (Prueba rápida de 1 minuto)

Si solo quieres probar que funciona básicamente:

```
"Paciente María Rodríguez, treinta años, sexo femenino.
Motivo de consulta: fiebre y tos.
Síntomas principales: fiebre, tos seca, dolor de garganta.
Presión arterial ciento veinte sobre ochenta.
Temperatura treinta y ocho punto cinco grados.
Diagnóstico: faringitis aguda, presuntivo.
Tratamiento: paracetamol quinientos miligramos cada ocho horas."
```

**Debe llenar:**
- ✅ Motivo de consulta ✓
- ✅ Síntomas principales ✓
- ✅ Diagnósticos ✓
- ✅ Tratamientos ✓
- **Progreso: 4/4** ✓

---

## 📊 RESULTADO ESPERADO FINAL

Al terminar el guion completo, deberías ver:

### Panel Izquierdo (Asistente IA):
```
Paciente femenina de 35 años que acude por cuadro febril de 5 días
de evolución, asociado a tos seca y odinofagia. Al examen: signos
vitales estables salvo temperatura de 38.5°C. Se diagnostica
faringitis aguda y se indica tratamiento analgésico y antiinflamatorio.
Continúa manejo de HTA. Control en 5 días.
```

### Panel Derecho (Formulario):
- **Progreso:** 4/4 (100%) ✅
- **Campos faltantes:** Ninguno
- **Sugerencias:** Ninguna
- **Todos los campos llenos** con los datos del guion

---

## 🔍 ANÁLISIS ESPERADO

### ¿El asistente IA lee TODO el contexto?
**SÍ**, porque el backend envía `state["final"]` completo en cada llamada:
```python
await stream_summary(ws, state["final"])  # Todo el transcript acumulado
```

### ¿El asistente usa las sugerencias enviadas?
**NO directamente**, las sugerencias son para el médico (UI), NO para la IA.
La IA solo recibe el transcript de voz.

### ¿Cómo mejorar el resumen?
Si quieres que la IA mencione los campos faltantes en su resumen,
debes modificar el prompt en `server.py:102-106` para incluir el
contexto de `missing` y `suggestions`.

---

¿TODO CLARO? ¡Ahora pruébalo! 🚀
