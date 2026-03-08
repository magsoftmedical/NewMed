# Integración Medberos AI - Guía Rápida

## Resumen

Se ha integrado la API de Medberos AI para predicción de:
- 🔍 **Diagnósticos** (con códigos CIE-10)
- 🧪 **Exámenes de laboratorio**
- 💊 **Tratamientos médicos**

## Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| [medberos_client.py](medberos_client.py) | Cliente HTTP para autenticación y llamadas a Medberos API |
| [medberos_mapper.py](medberos_mapper.py) | Conversión entre formatos Consult-IA ↔ Medberos |
| [test_medberos.py](test_medberos.py) | Script de pruebas para validar integración |
| [medberos_examples.json](medberos_examples.json) | Ejemplos de requests/responses |
| [MEDBEROS_INTEGRATION.md](MEDBEROS_INTEGRATION.md) | Documentación completa |

## Configuración Rápida

### Paso 1: Obtener Credenciales

1. Accede a https://test-api.medberos.com
2. Inicia sesión con jaminyauricajas@gmail.com
3. Clic en ícono de llave → "Crear API Key"
4. Ingresa dominio: `https://tima.medberos.com`
5. Copia API Key y Secret

### Paso 2: Configurar .env

Edita [.env](.env) y completa:

```env
MEDBEROS_API_URL=https://test-api.medberos.com/api
MEDBEROS_API_KEY=tu_api_key_aqui
MEDBEROS_API_SECRET=tu_secret_aqui
```

### Paso 3: Probar la Integración

```bash
# Desde consultia/backend
python test_medberos.py
```

Si todo está bien, deberías ver:

```
✅ Autenticación exitosa
✅ Predicción de diagnósticos exitosa
✅ Predicción de exámenes exitosa
✅ Predicción de tratamientos exitosa
🎉 ¡Todos los tests pasaron exitosamente!
```

## Endpoints Disponibles

### GET /medberos/test
Verifica conexión con Medberos API.

```bash
curl http://localhost:8001/medberos/test
```

### POST /medberos/predict-diagnoses
Predice diagnósticos basados en síntomas y datos del paciente.

```bash
curl -X POST http://localhost:8001/medberos/predict-diagnoses \
  -H "Content-Type: application/json" \
  -d '{
    "form": {
      "anamnesis": {
        "sintomasPrincipales": ["fiebre", "tos", "dolor de cabeza"]
      }
    },
    "doctorComments": "Posible cuadro gripal"
  }'
```

### POST /medberos/predict-exams
Predice exámenes médicos recomendados.

### POST /medberos/predict-treatments
Predice tratamientos basados en diagnósticos.

## Uso con TIMA (Voice-to-Text)

El flujo ideal es:

```
Médico habla → TIMA transcribe → Actualiza formulario
                                        ↓
                    Llama a Medberos AI con formulario + transcripción
                                        ↓
                    Medberos devuelve predicciones (diagnósticos/exámenes/tratamientos)
                                        ↓
                    TIMA muestra sugerencias al médico
                                        ↓
                    Médico acepta/modifica/rechaza
```

### Ejemplo de Integración

```python
# En el flujo de WebSocket cuando llega transcripción final
async def on_final_transcript(transcript, current_form):
    # 1. Actualizar formulario con OpenAI (ya existe)
    updated_form = await extract_form(transcript)

    # 2. Llamar a Medberos para predicciones (NUEVO)
    payload = consultia_to_medberos_payload(updated_form, transcript)

    # Predicción de diagnósticos
    diagnoses = await medberos_client.predict_diagnoses(payload)

    # Predicción de exámenes
    exams = await medberos_client.predict_exams(payload)

    # Predicción de tratamientos (si ya hay diagnósticos)
    if updated_form.get("diagnosticos"):
        treatments = await medberos_client.predict_treatments(payload)

    # 3. Enviar predicciones al frontend
    await ws.send_json({
        "type": "ai_predictions",
        "diagnoses": diagnoses,
        "exams": exams,
        "treatments": treatments
    })
```

## Campo DoctorComments (IMPORTANTE)

El campo `doctorComments` es **CLAVE** para mejorar las predicciones:

- ✅ Incluye la transcripción completa de lo que dijo el médico
- ✅ Incluye contexto adicional no estructurado
- ✅ La IA de Medberos lo usa para entender mejor el caso

**Ejemplos:**

```json
{
  "doctorComments": "Paciente refiere dolor abdominal en cuadrante inferior derecho desde hace 6 horas. Sospecha de apendicitis. Tiene antecedentes de cirugía abdominal previa."
}
```

```json
{
  "doctorComments": "Cuadro compatible con infección respiratoria viral. Paciente trabaja en guardería, alta exposición a virus. Hermana tuvo gripe la semana pasada."
}
```

## Autenticación Automática

El cliente maneja automáticamente:

- ✅ Autenticación inicial con API Key/Secret
- ✅ Obtención de JWT token
- ✅ Renovación automática (token expira cada 2 horas)
- ✅ Caché en memoria

**No necesitas preocuparte por la autenticación** - el cliente lo hace transparentemente.

## Logs

Todos los logs usan el logger de uvicorn:

```
[MEDBEROS] Authenticating with API Key/Secret...
[MEDBEROS] Authentication successful. Token valid until 2025-11-24 16:30:00
[MEDBEROS] Calling predictDiagnoses...
[MEDBEROS] predictDiagnoses successful. Got 3 predictions
```

## Próximos Pasos

### Backend ✅
- [x] Cliente de autenticación
- [x] Endpoints REST para predicciones
- [x] Mapeo de formatos
- [x] Tests automatizados

### Frontend (Pendiente)
- [ ] Componente para mostrar predicciones en UI
- [ ] Botones "Aceptar/Rechazar" sugerencias
- [ ] Integración con flujo de voz de TIMA
- [ ] Panel lateral con predicciones en tiempo real
- [ ] Indicador visual de confianza (ej: barras de porcentaje)

### Testing (Pendiente)
- [ ] Probar con JSONs reales de Daniel
- [ ] Validar mapeo de campos con casos reales
- [ ] Ajustar formato según respuestas reales de API
- [ ] Testing de integración frontend-backend

## Troubleshooting

### Error: "Authentication failed"

✅ Verifica que `MEDBEROS_API_KEY` y `MEDBEROS_API_SECRET` estén en `.env`

✅ Verifica que las credenciales sean correctas (prueba en https://test-api.medberos.com)

### Error: "No module named httpx"

```bash
pip install httpx
```

### Error: "Connection timeout"

La API de Medberos puede tardar algunos segundos. El timeout está configurado en 30 segundos.

Si sigue fallando, verifica tu conexión a internet.

## Contacto

- **API de Medberos:** Daniel Adrianzen-Alvarez
- **Ambiente de desarrollo:** https://test-api.medberos.com
- **Documentación completa:** [MEDBEROS_INTEGRATION.md](MEDBEROS_INTEGRATION.md)

---

**Nota:** Esta integración usa el ambiente de **desarrollo** de Medberos. Para producción, actualizar la URL en `.env`.
