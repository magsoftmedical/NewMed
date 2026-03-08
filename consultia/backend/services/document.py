import base64
import io
import json

from fastapi import UploadFile

from config import client, logger


async def extract_document(file: UploadFile) -> dict:
    """
    Extract structured medical data from an uploaded image or PDF.
    Uses OpenAI Vision API (GPT-4o).
    Returns parsed JSON dict on success.
    Raises on errors.
    """
    logger.info(f"[EXTRACT-DOC] Received file: {file.filename}, content_type: {file.content_type}")

    contents = await file.read()

    is_pdf = file.content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")

    if is_pdf:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(contents, first_page=1, last_page=1)
        if not images:
            raise ValueError("No se pudo convertir el PDF a imagen")

        img_byte_arr = io.BytesIO()
        images[0].save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)
        image_data = img_byte_arr.getvalue()
    else:
        image_data = contents

    base64_image = base64.b64encode(image_data).decode("utf-8")

    system_prompt = """Eres un experto en digitalización de historias clínicas médicas.

            Tu tarea es extraer TODA la información visible en el documento médico y estructurarla en formato JSON.

            IMPORTANTE:
            - Extrae TODOS los datos que veas, incluso si están incompletos
            - Si un campo no está presente, omítelo del JSON (no pongas null ni cadenas vacías)
            - Mantén la terminología médica original
            - Para fechas, usa formato ISO (YYYY-MM-DD) si es posible
            - Para arrays (síntomas, diagnósticos, tratamientos), incluye todos los items que encuentres

            ESTRUCTURA ESPERADA:
            {
            "afiliacion": {
                "nombreCompleto": "nombre del paciente",
                "edad": {"anios": número, "meses": número},
                "sexo": "M/F",
                "dni": "documento",
                "grupoSangre": "tipo sangre",
                "fechaHora": "fecha consulta",
                "seguro": "nombre seguro",
                "tipoConsulta": "tipo",
                "numeroSeguro": "número",
                "motivoConsulta": "motivo"
            },
            "anamnesis": {
                "tiempoEnfermedad": "duración",
                "sintomasPrincipales": ["síntoma1", "síntoma2"],
                "relato": "narrativa completa",
                "funcionesBiologicas": {
                "apetito": "estado",
                "sed": "estado",
                "orina": "estado",
                "deposiciones": "estado",
                "sueno": "estado"
                },
                "antecedentes": {
                "personales": ["antecedente1"],
                "padre": ["antecedente paterno"],
                "madre": ["antecedente materno"]
                },
                "alergias": ["alergia1"],
                "medicamentos": ["medicamento1"]
            },
            "examenClinico": {
                "signosVitales": {
                "PA": "presión arterial",
                "FC": frecuencia cardiaca (número),
                "FR": frecuencia respiratoria (número),
                "temperatura": "temperatura",
                "SpO2": "saturación",
                "IMC": "índice masa corporal",
                "peso": peso en kg,
                "talla": talla en cm
                },
                "estadoGeneral": "descripción",
                "descripcionGeneral": "hallazgos",
                "sistemas": {
                "piel": "hallazgos",
                "cabeza": "hallazgos",
                "cuello": "hallazgos",
                "torax": "hallazgos",
                "pulmones": "hallazgos",
                "corazon": "hallazgos",
                "abdomen": "hallazgos",
                "extremidades": "hallazgos",
                "neurologico": "hallazgos"
                }
            },
            "diagnosticos": [
                {"nombre": "diagnóstico", "cie10": "código", "tipo": "Presuntivo/Definitivo/Diferencial"}
            ],
            "tratamientos": [
                {"medicamento": "nombre", "dosisIndicacion": "dosis e indicaciones", "gtin": "código"}
            ],
            "firma": {
                "medico": "nombre médico",
                "colegiatura": "número colegiatura",
                "fecha": "fecha"
            }
            }

            Devuelve SOLO el JSON, sin explicaciones adicionales."""

    user_prompt = "Extrae toda la información de esta historia clínica y estructúrala según el formato solicitado."

    logger.info("[EXTRACT-DOC] Calling OpenAI Vision API...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=4000,
        temperature=0.1,
    )

    content = response.choices[0].message.content
    logger.info(f"[EXTRACT-DOC] OpenAI response received: {len(content)} chars")

    # Clean markdown-wrapped JSON if present
    if content.strip().startswith("```"):
        lines = content.strip().split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("```"):
                in_json = not in_json
                continue
            if in_json:
                json_lines.append(line)
        content = "\n".join(json_lines)

    extracted_data = json.loads(content)
    logger.info("[EXTRACT-DOC] Successfully parsed JSON")
    return extracted_data
