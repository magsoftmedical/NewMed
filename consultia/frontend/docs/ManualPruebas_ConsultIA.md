# Manual de Pruebas – ConsultIA

## 1. Objetivo
Validar que la aplicación **ConsultIA** reconozca y gestione correctamente **campo por campo** en la historia clínica electrónica:  
- Motivo de consulta  
- Síntomas principales  
- Diagnósticos  
- Tratamientos  

Así como la integración con **STT (transcripción de voz)**, **IA (sugerencias)** y las funciones de **validación/exportación**.

---

## 2. Alcance
- **Backend (FastAPI)**: `server.py`, `constants.py` (`REQUIRED_KEYS`)  
- **Frontend (Angular)**:  
  - `consultation-room.component.ts/html`  
  - `ai-stream-panel.component.ts/html`  
  - `transcript-form.service.ts`  

---

## 3. Requisitos previos
- Backend corriendo en `http://127.0.0.1:8000`  
- Frontend Angular (`ng serve`)  
- Postman/cURL para pruebas de API  
- Navegador con DevTools abiertos  

---

## 4. Casos de prueba

### TC-01 – Form vacío
- **Acción**: Abrir la pantalla y validar.  
- **Esperado**: “Campos faltantes” = 4 (`motivoConsulta`, `sintomasPrincipales`, `diagnosticos`, `tratamientos`).  

### TC-02 – Completar Motivo
- **Acción**: Llenar *motivo de consulta* y validar.  
- **Esperado**: Faltantes = 3.  

### TC-03 – Completar Síntomas
- **Acción**: Llenar *síntomas principales*.  
- **Esperado**: Faltantes = 2.  

### TC-04 – Añadir Diagnóstico
- **Acción**: Añadir 1 diagnóstico completo (nombre, tipo, CIE-10).  
- **Esperado**: Faltantes = 1 (solo tratamientos).  

### TC-05 – Añadir Tratamiento
- **Acción**: Añadir 1 tratamiento completo (medicamento + dosis).  
- **Esperado**: Faltantes = vacío → botón **Guardar** habilitado.  

### TC-06 – Prueba con STT
- **Acción**: Dictar “Motivo de consulta: dolor abdominal. Síntomas: fiebre, náuseas, diarrea.”  
- **Esperado**: Los campos se llenan automáticamente, faltantes se actualizan.  

### TC-07 – Sugerencias IA
- **Acción**: Pulsar en una sugerencia del panel IA.  
- **Esperado**: El campo asociado se llena o se añade un ítem.  

### TC-08 – Exportación
- **Acción**: Exportar a TXT y PDF.  
- **Esperado**: Documentos incluyen los 4 campos requeridos + listas completas.  

---

## 5. Checklist rápido
- [ ] Backend responde `/hce/validate`.  
- [ ] Front conectado al backend.  
- [ ] Form vacío → 4 faltantes.  
- [ ] Secuencia 4→3→2→1→0 faltantes al llenar.  
- [ ] STT llena motivo/síntomas.  
- [ ] IA rellena campos cuando aplica.  
- [ ] Guardar habilitado con 0 faltantes.  
- [ ] Exportación genera documentos correctos.  

---

## 6. Reporte de defectos (plantilla)
**Título:** [Módulo] Problema  
**Severidad:** Alta / Media / Baja  
**Pasos para reproducir:**  
1. …  
2. …  
**Resultado actual:** …  
**Resultado esperado:** …  
**Evidencia:** captura/logs  
