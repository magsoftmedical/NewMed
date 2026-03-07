# Integración con Medberos AI API

## Configuración Inicial

### 1. Obtener API Key y Secret

1. Accede a https://test-api.medberos.com (ambiente de desarrollo)
2. Usa las credenciales que te enviaron a jaminyauricajas@gmail.com
3. En la barra de navegación izquierda, haz clic en el ícono de llave
4. Haz clic en "Crear API Key"
5. Ingresa un dominio o IP válido (ej: `https://tima.medberos.com`)
6. Copia el API Key y Secret generados

### 2. Configurar el Backend

Edita el archivo `.env` y completa:

```env
MEDBEROS_API_URL=https://test-api.medberos.com/api
MEDBEROS_API_KEY=tu_api_key_aqui
MEDBEROS_API_SECRET=tu_secret_aqui
```

### 3. Instalar Dependencia

El cliente usa `httpx` para requests async:

```bash
pip install httpx
```

## Endpoints Disponibles

### 1. Test de Conexión

```http
GET /medberos/test
```

Verifica que la autenticación funciona correctamente.

**Respuesta:**
```json
{
  "ok": true,
  "message": "Connection successful"
}
```

### 2. Predicción de Diagnósticos

```http
POST /medberos/predict-diagnoses
Content-Type: application/json

{
  "form": {
    "afiliacion": {
      "edad": {"anios": 35},
      "sexo": "F"
    },
    "anamnesis": {
      "sintomasPrincipales": ["fiebre", "tos", "dolor de cabeza"]
    },
    "examenClinico": {
      "signosVitales": {
        "temperatura": 38.5,
        "PA": "120/80"
      }
    }
  },
  "doctorComments": "Paciente refiere que podría ser una gripe. Tiene tos seca y fiebre desde hace 3 días."
}
```

**Respuesta:**
```json
{
  "success": true,
  "diagnosticos": [
    {
      "nombre": "Gripe",
      "cie10": "J11.1",
      "tipo": "Presuntivo",
      "confianza": 0.85
    }
  ]
}
```

### 3. Predicción de Exámenes

```http
POST /medberos/predict-exams
Content-Type: application/json

{
  "form": { /* mismo formato */ },
  "doctorComments": "Solicitar exámenes de laboratorio para descartar infección"
}
```

### 4. Predicción de Tratamientos

```http
POST /medberos/predict-treatments
Content-Type: application/json

{
  "form": { /* mismo formato */ },
  "doctorComments": "Prescribir analgésicos y antipiréticos"
}
```

## Flujo de Autenticación

El cliente maneja automáticamente:

1. Autenticación inicial con API Key/Secret
2. Obtención de JWT token
3. Renovación automática (token expira cada 2 horas)
4. Caché del token en memoria

No necesitas preocuparte por la autenticación - el cliente lo hace transparentemente.

## Uso de DoctorComments

El campo `doctorComments` es CLAVE para mejorar las predicciones:

- Incluye cualquier información relevante que diga el médico via TIMA
- No tiene que ser completa ni estructurada
- La IA de Medberos usa este contexto adicional para mejorar sus predicciones

**Ejemplos:**

```json
{
  "doctorComments": "Paciente refiere dolor abdominal en cuadrante inferior derecho. Sospecha de apendicitis."
}
```

```json
{
  "doctorComments": "Posible infección respiratoria. Tiene antecedentes de asma."
}
```

## Mapeo de Campos

El sistema mapea automáticamente entre formatos:

### Consult-IA → Medberos

| Campo Consult-IA | Campo Medberos |
|------------------|----------------|
| `afiliacion.edad.anios` | `PatientAge` |
| `afiliacion.sexo` | `PatientSex` |
| `anamnesis.sintomasPrincipales` | `Symptoms` |
| `examenClinico.signosVitales.PA` | `VitalSigns.BloodPressure` |
| `examenClinico.signosVitales.FC` | `VitalSigns.HeartRate` |
| `examenClinico.signosVitales.temperatura` | `VitalSigns.Temperature` |

Ver [medberos_mapper.py](medberos_mapper.py) para el mapeo completo.

## Testing

### Desde Python

```python
from medberos_client import medberos_client

# Test de conexión
result = await medberos_client.test_connection()
print(result)

# Predicción de diagnósticos
payload = {
    "PatientAge": 35,
    "PatientSex": "F",
    "Symptoms": ["fiebre", "tos"],
    "DoctorComments": "Posible gripe"
}

result = await medberos_client.predict_diagnoses(payload)
print(result)
```

### Desde cURL

```bash
# Test
curl http://localhost:8001/medberos/test

# Predicción
curl -X POST http://localhost:8001/medberos/predict-diagnoses \
  -H "Content-Type: application/json" \
  -d '{
    "form": {
      "afiliacion": {"edad": {"anios": 35}, "sexo": "F"},
      "anamnesis": {"sintomasPrincipales": ["fiebre", "tos"]}
    },
    "doctorComments": "Posible gripe"
  }'
```

## Integración con TIMA (WebSocket)

Para integrar las predicciones en el flujo de voz de TIMA:

1. Cuando el médico termine de dictar información relevante
2. Llamar a los endpoints de predicción con el formulario actual y la transcripción
3. Mostrar las predicciones al médico como sugerencias
4. El médico puede aceptar, modificar o rechazar las sugerencias

**Ejemplo de flujo:**

```
Médico: "Paciente de 35 años con fiebre y tos desde hace 3 días"
  ↓
[TIMA procesa la voz y actualiza el formulario]
  ↓
[Backend llama a Medberos AI con formulario + transcripción]
  ↓
[Medberos devuelve predicciones: "Gripe (J11.1)" con 85% confianza]
  ↓
[TIMA muestra sugerencia al médico]
  ↓
Médico acepta o modifica el diagnóstico
```

## Logs

El cliente registra todas las operaciones:

```
[MEDBEROS] Authenticating with API Key/Secret...
[MEDBEROS] Authentication successful. Token valid until 2025-11-24 16:30:00
[MEDBEROS] Calling predictDiagnoses...
[MEDBEROS] predictDiagnoses successful. Got 3 predictions
```

Útil para debugging y monitoreo.

## Limitaciones Actuales

- Token expira cada 2 horas (manejado automáticamente)
- Ambiente de desarrollo (`test-api.medberos.com`)
- No hay validación de dominio/IP por ahora (según Daniel, será agregada después)

## Próximos Pasos

1. ✅ Configurar API Key/Secret en `.env`
2. ✅ Probar endpoint `/medberos/test`
3. ✅ Revisar ejemplos de JSONs que enviará Daniel
4. ⏳ Integrar predicciones en el componente de TIMA (frontend Angular)
5. ⏳ Agregar UI para mostrar predicciones al médico
6. ⏳ Implementar aceptación/rechazo de sugerencias

## Soporte

Para problemas con la API de Medberos, contactar a Daniel Adrianzen-Alvarez.
