# 🎤 GUION DE PRUEBA - LENGUAJE NATURAL

## 🎯 OBJETIVO
Probar el sistema con lenguaje REAL de consulta médica, sin términos técnicos forzados.

---

## ✅ MEJORAS IMPLEMENTADAS

### 1. **Detección de motivo de consulta mejorada**
- Ya NO necesitas decir "motivo de consulta es..."
- Detecta frases naturales: "viene por...", "tiene...", "paciente con..."

### 2. **Detección de diagnósticos flexible**
- Ya NO necesitas decir "diagnóstico: faringitis aguda código CIE..."
- Detecta: "parece una gripe", "probable faringitis", "se trata de..."

### 3. **Detección de tratamientos natural**
- Ya NO necesitas decir "tratamiento: paracetamol 500mg vía oral..."
- Detecta: "le voy a dar paracetamol", "que tome una pastilla..."

---

## 🎬 GUION REALISTA (2-3 minutos)

### **Inicio de consulta (habla natural):**

```
"Buenas tardes. Paciente de nombre María Rodríguez, tiene 35 años.
Es mujer. DNI setenta y seis millones quinientos cuarenta y tres mil doscientos dieciocho.
Viene por fiebre que empezó hace tres días."
```

**Campos esperados:**
- ✅ nombreCompleto: "María Rodríguez"
- ✅ edad.anios: 35
- ✅ sexo: "femenino"
- ✅ dni: "76543218"
- ✅ **motivoConsulta: "fiebre"** ← Detectado sin decir "motivo de consulta"

**Progreso:** 1/4 (25%)

---

### **Síntomas (habla natural):**

```
"La paciente me dice que tiene fiebre, tos seca y le duele la garganta.
Empezó hace tres días. La fiebre le sube hasta 39 grados.
Está comiendo poco, pero toma agua normal. Duerme mal por la tos."
```

**Campos esperados:**
- ✅ **sintomasPrincipales: ["fiebre", "tos seca", "dolor de garganta"]**
- ✅ tiempoEnfermedad: "3 días"
- ✅ anamnesis.relato: (descripción completa)
- ✅ funcionesBiologicas.apetito: "disminuido"
- ✅ funcionesBiologicas.sed: "normal"
- ✅ funcionesBiologicas.sueno: "interrumpido"

**Progreso:** 2/4 (50%)

---

### **Examen físico (habla natural):**

```
"Al examinarla, presión 120 sobre 80.
Pulso 85. Respirando 18 veces por minuto.
Temperatura treinta y ocho punto cinco grados.
Saturación noventa y ocho por ciento.
Pesa 65 kilos, mide un metro sesenta y cinco."
```

**Campos esperados:**
- ✅ PA: "120/80"
- ✅ FC: 85
- ✅ FR: 18
- ✅ temperatura: 38.5
- ✅ SpO2: 98
- ✅ peso: 65
- ✅ talla: 165

```
"La garganta está bien roja e inflamada.
Los pulmones suenan bien.
El corazón normal."
```

**Campos esperados:**
- ✅ sistemas.cuello: (descripción de garganta)
- ✅ sistemas.pulmones: "suenan bien" / "murmullo vesicular normal"
- ✅ sistemas.corazon: "normal"

---

### **Diagnóstico (habla TOTALMENTE natural):**

```
"Bueno, esto parece una faringitis.
Probablemente por un virus.
También tiene hipertensión controlada."
```

**Campos esperados:**
- ✅ **diagnosticos:**
  - [0]: {nombre: "faringitis", tipo: "presuntivo"}
  - [1]: {nombre: "hipertensión", tipo: "definitivo"}

**Progreso:** 3/4 (75%)

**NOTA:** Ya NO necesitas decir "diagnóstico presuntivo faringitis aguda CIE J02.9"

---

### **Tratamiento (habla TOTALMENTE natural):**

```
"Le voy a dar paracetamol para la fiebre.
Que tome una pastilla de 500 cada 8 horas.
También ibuprofeno si le duele mucho, 400 miligramos cada 12 horas.
Y que tome harta agua y descanse."
```

**Campos esperados:**
- ✅ **tratamientos:**
  - [0]: {medicamento: "paracetamol", dosisIndicacion: "500mg cada 8 horas"}
  - [1]: {medicamento: "ibuprofeno", dosisIndicacion: "400mg cada 12 horas"}
  - [2]: {medicamento: "abundantes líquidos", dosisIndicacion: "reposo"}

**Progreso:** 4/4 (100%) ✅

**NOTA:** Ya NO necesitas decir "tratamiento: paracetamol 500mg vía oral cada 8 horas por 5 días"

---

## 🆚 COMPARACIÓN: ANTES vs AHORA

### **MOTIVO DE CONSULTA**

| ANTES (requería) | AHORA (detecta) |
|------------------|-----------------|
| ❌ "El motivo de consulta es fiebre alta" | ✅ "Viene por fiebre" |
| ❌ "Acude para control de presión" | ✅ "Paciente con fiebre desde hace 3 días" |
| | ✅ "Tiene dolor de cabeza" |

---

### **SÍNTOMAS PRINCIPALES**

| ANTES (requería) | AHORA (detecta) |
|------------------|-----------------|
| ❌ "Los síntomas principales son fiebre tos y cefalea" | ✅ "Tiene fiebre, tos y le duele la cabeza" |
| | ✅ "Me dice que le duele el estómago" |
| | ✅ "Presenta náuseas y vómito" |

---

### **DIAGNÓSTICOS**

| ANTES (requería) | AHORA (detecta) |
|------------------|-----------------|
| ❌ "Diagnóstico presuntivo faringitis aguda CIE J02.9" | ✅ "Parece una faringitis" |
| ❌ "Diagnóstico definitivo hipertensión arterial I10" | ✅ "Probablemente es una gripe" |
| | ✅ "Se trata de una infección viral" |
| | ✅ "Tiene la presión alta" |
| | ✅ "Compatible con gastritis" |

---

### **TRATAMIENTOS**

| ANTES (requería) | AHORA (detecta) |
|------------------|-----------------|
| ❌ "Tratamiento paracetamol 500mg vía oral cada 8 horas" | ✅ "Le voy a dar paracetamol" |
| ❌ "Indicar ibuprofeno 400mg cada 12 horas por 3 días" | ✅ "Que tome una pastilla cada 8 horas" |
| | ✅ "Le receto ibuprofeno para el dolor" |
| | ✅ "Continúe con su medicación de la presión" |
| | ✅ "Reposo y tomar mucha agua" |

---

## 📋 EJEMPLOS DE FRASES REALES

### ✅ ESTAS FRASES AHORA FUNCIONAN:

**Motivo de consulta:**
- "Paciente viene por dolor de estómago"
- "Tiene fiebre desde ayer"
- "Consulta por control de azúcar"
- "Vino porque no puede dormir"

**Diagnósticos:**
- "Esto es una gripe"
- "Parece gastritis"
- "Probable infección urinaria"
- "Sospecho de anemia"
- "Compatible con migraña"
- "Tiene diabetes"

**Tratamientos:**
- "Dale omeprazol en ayunas"
- "Que tome aspirina si le duele"
- "Le voy a recetar antibiótico"
- "Continúa con tu medicación"
- "Reposo por tres días"
- "Una cucharada cada 8 horas"

---

## 🎯 PRUEBA RÁPIDA (1 minuto)

```
"Paciente Juan López, 42 años, hombre.
Viene por dolor de cabeza fuerte desde ayer.
Le duele acá atrás (nuca) y tiene náuseas.
Presión 140 sobre 90, está un poco alta.
Parece ser una cefalea tensional por estrés.
Le voy a dar ibuprofeno 400, que tome una cada 8 horas.
Y que descanse, no computadora ni celular."
```

**Debe llenar:**
- ✅ motivoConsulta: "dolor de cabeza"
- ✅ sintomasPrincipales: ["dolor de cabeza", "náuseas"]
- ✅ PA: "140/90"
- ✅ diagnosticos: [{nombre: "cefalea tensional", tipo: "presuntivo"}]
- ✅ tratamientos: [{medicamento: "ibuprofeno", dosisIndicacion: "400mg cada 8 horas"}]

**Progreso:** 4/4 ✅

---

## 🐛 SI ALGO NO FUNCIONA

### Problema 1: "El asistente IA no aparece"

**Verifica en la terminal del backend:**
```
[AI] stream_summary ENTER len=..., missing=[...]
```

Si NO aparece → Hay un error antes. Revisa la consola completa del backend.

**Posibles causas:**
1. Error de OpenAI (API key inválida, sin créditos)
2. Error de sintaxis en server.py
3. El WebSocket no está conectado

**Solución rápida:**
```bash
# Detén el servidor (Ctrl+C)
# Vuelve a iniciar
cd consultia\backend
.venv\Scripts\activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

### Problema 2: "No detecta motivo de consulta"

**Prueba diciendo más claro:**
- ✅ "Paciente viene por fiebre"
- ✅ "Acude por dolor"
- ✅ "Tiene tos"

Si aún no funciona, revisa los logs del backend para ver qué está extrayendo:
```
[WS] form_update: {...}
```

---

### Problema 3: "No detecta diagnósticos"

**Asegúrate de mencionar una CONDICIÓN, no solo síntomas:**
- ❌ "Tiene fiebre y tos" (son síntomas, no diagnóstico)
- ✅ "Parece una gripe" (es una condición)
- ✅ "Probable faringitis" (es un diagnóstico)

---

### Problema 4: "No detecta tratamientos"

**Menciona el medicamento de forma más explícita:**
- ❌ "Que se tome algo para el dolor" (muy vago)
- ✅ "Le doy paracetamol"
- ✅ "Que tome ibuprofeno"

---

## 📊 MÉTRICAS DE ÉXITO

Después de probar, verifica:

- [ ] El asistente IA genera resumen en el panel izquierdo
- [ ] El motivo de consulta se detecta sin decir "motivo de consulta"
- [ ] Los síntomas se detectan con lenguaje natural
- [ ] Los diagnósticos se detectan diciendo "parece...", "probable..."
- [ ] Los tratamientos se detectan diciendo "le doy...", "que tome..."
- [ ] El progreso llega a 4/4
- [ ] No quedan campos faltantes
- [ ] El asistente IA menciona los pendientes inicialmente
- [ ] Al completar, el asistente ya NO menciona pendientes

---

## 🚀 SIGUIENTE PASO

1. Ejecuta: `INICIAR_PROYECTO.bat`
2. Abre: http://localhost:4200
3. Habla usando este guion natural
4. Verifica que TODO funcione

Si encuentras problemas, comparte:
- Los logs de la terminal del backend
- Qué dijiste exactamente
- Qué campos se llenaron y cuáles no

---

¡Ahora prueba con lenguaje totalmente natural! 🎉
