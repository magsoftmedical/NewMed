"""
Mapper para convertir entre el formato de Consult-IA y Medberos API.

Basado en los ejemplos reales de la API de Medberos.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("uvicorn.error")


def consultia_to_medberos_payload(form: Dict[str, Any], doctor_comments: str = "") -> Dict[str, Any]:
    """
    Convierte el formulario de Consult-IA al formato REAL de Medberos.

    Formato según ejemplos de API:
    - Age: string (no número)
    - Sex: "Masculino" o "Femenino" (no M/F)
    - Symptoms: string (no array)
    - VitalFunctions: objeto con campos específicos
    - Diagnoses: array de {CieCode, Type}
    - Campos requeridos: RequesterId, PatientId, TicketId, NoteId
    """

    payload = {
        # Campos requeridos con valores por defecto
        "RequesterId": 1,
        "PatientId": 0,
        "TicketId": 0,
        "NoteId": 0,
        "SpecialtyId": 1  # 1 = Medicina General
    }

    # ========== DATOS DEL PACIENTE ==========
    afiliacion = form.get("afiliacion", {})

    # Edad (string)
    edad_obj = afiliacion.get("edad", {})
    edad_anios = edad_obj.get("anios")
    if edad_anios:
        payload["Age"] = str(edad_anios)

    # Sexo (normalizar a Masculino/Femenino)
    sexo = afiliacion.get("sexo", "")
    if sexo:
        if sexo.upper() in ["M", "MALE", "MASCULINO", "HOMBRE"]:
            payload["Sex"] = "Masculino"
        elif sexo.upper() in ["F", "FEMALE", "FEMENINO", "MUJER"]:
            payload["Sex"] = "Femenino"
        else:
            payload["Sex"] = sexo

    # ========== ANAMNESIS ==========
    anamnesis = form.get("anamnesis", {})

    # Síntomas (convertir array a string)
    sintomas = anamnesis.get("sintomasPrincipales", [])
    if sintomas:
        # Unir síntomas con comas
        payload["Symptoms"] = ", ".join(sintomas)

    # Relato/descripción
    relato = anamnesis.get("relato", "")
    if relato:
        payload["Description"] = relato
    elif sintomas:
        # Si no hay relato, usar síntomas como descripción
        payload["Description"] = ", ".join(sintomas)

    # ========== SIGNOS VITALES ==========
    examen = form.get("examenClinico", {})
    signos_vitales = examen.get("signosVitales", {})

    if signos_vitales:
        vital_functions = {}

        # Presión arterial (separar en sistólica/diastólica)
        pa = signos_vitales.get("PA", "")
        if pa and "/" in pa:
            partes = pa.split("/")
            vital_functions["SystolicBloodPressure"] = partes[0].strip()
            vital_functions["DiastolicBloodPressure"] = partes[1].strip()

        # Frecuencia cardíaca
        fc = signos_vitales.get("FC")
        if fc:
            vital_functions["HeartRate"] = str(fc)

        # Temperatura
        temp = signos_vitales.get("temperatura")
        if temp:
            # Eliminar unidades si existen (ej: "38.5°C" → "38.5")
            temp_str = str(temp).replace("°C", "").replace("°", "").strip()
            vital_functions["Temperature"] = temp_str

        # Saturación
        spo2 = signos_vitales.get("SpO2")
        if spo2:
            # Eliminar % si existe
            spo2_str = str(spo2).replace("%", "").strip()
            vital_functions["Saturation"] = spo2_str

        # Frecuencia respiratoria
        fr = signos_vitales.get("FR")
        if fr:
            vital_functions["BreathingRate"] = str(fr)

        # Peso y talla
        peso = signos_vitales.get("peso")
        if peso:
            vital_functions["Weight"] = str(peso)

        talla = signos_vitales.get("talla")
        if talla:
            vital_functions["Size"] = str(talla)

        # IMC
        imc = signos_vitales.get("IMC")
        if imc:
            vital_functions["Bmi"] = str(imc)

        if vital_functions:
            payload["VitalFunctions"] = vital_functions

    # ========== EXAMEN FÍSICO ==========
    sistemas = examen.get("sistemas", {})
    if sistemas:
        physical_exam = {}

        # Abdomen
        abdomen = sistemas.get("abdomen", "")
        if abdomen:
            # Determinar campos booleanos basados en descripción
            physical_exam["SoftAbdomen"] = "blando" in abdomen.lower()
            physical_exam["NoisesAbdomen"] = "ruidos" in abdomen.lower() or "peristalsis" in abdomen.lower()
            physical_exam["WithOutLiverAbdomen"] = "hepatomegalia" not in abdomen.lower()
            physical_exam["TumorsAbdomen"] = "masa" in abdomen.lower() or "tumor" in abdomen.lower()
            physical_exam["DetailsSoftAbdomen"] = abdomen

        # Extremidades
        extremidades = sistemas.get("extremidades", "")
        if extremidades:
            physical_exam["WithoutAlterationsExtremities"] = "sin alteraciones" in extremidades.lower() or "normales" in extremidades.lower()

        # Neurológico
        neurologico = sistemas.get("neurologico", "")
        if neurologico:
            physical_exam["NeurologicalExamConscienceLevel"] = 15  # Glasgow por defecto
            physical_exam["NeurologicalExamDescription"] = neurologico

        if physical_exam:
            payload["PhysicalExam"] = physical_exam

    # ========== DIAGNÓSTICOS ==========
    diagnosticos = form.get("diagnosticos", [])
    if diagnosticos:
        diagnoses = []
        for diag in diagnosticos:
            cie10 = diag.get("cie10", "")
            tipo = diag.get("tipo", "Presuntivo")

            if cie10:
                diagnoses.append({
                    "CieCode": cie10,
                    "Type": tipo
                })

        if diagnoses:
            payload["Diagnoses"] = diagnoses

    # ========== COMENTARIOS DEL DOCTOR ==========
    if doctor_comments:
        payload["DoctorComments"] = doctor_comments

    logger.debug(f"[MAPPER] Converted to Medberos format: {len(payload)} fields")

    return payload


def medberos_diagnoses_to_consultia(predictions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convierte predicciones de diagnósticos al formato de Consult-IA."""
    import json
    diagnosticos = []

    print("\n" + "="*80)
    print(f"[MAPPER] Processing {len(predictions)} predictions")
    print("="*80)

    for i, pred in enumerate(predictions):
        print(f"\n[MAPPER] Prediction {i}:")
        print(json.dumps(pred, indent=2, ensure_ascii=False))
        print(f"[MAPPER] Keys available: {list(pred.keys())}")

        # Los campos reales de la API de Medberos son:
        # - "title": nombre del diagnóstico
        # - "code": código CIE-10
        # - "id", "deleted", "chapterId", "chapter": metadatos (no usados)

        nombre = pred.get("title") or pred.get("Title") or ""

        # El código viene sin punto, ej: "G440" debe ser "G44.0"
        code_raw = pred.get("code") or pred.get("Code") or ""
        # Intentar formatear el código CIE-10 agregando el punto
        if code_raw and len(code_raw) >= 4:
            # Formato: G44.0 (letra + 2 dígitos + punto + dígito)
            cie10 = f"{code_raw[:3]}.{code_raw[3:]}"
        else:
            cie10 = code_raw

        # Medberos no devuelve confianza para diagnósticos, usar valor por defecto
        confidence = 0.85  # Confianza por defecto

        print(f"[MAPPER] ✅ Extracted - nombre: '{nombre}', cie10: '{cie10}', confidence: {confidence}")

        diagnostico = {
            "nombre": nombre,
            "cie10": cie10,
            "tipo": "Presuntivo"
        }

        # Agregar confianza si existe
        if confidence is not None:
            diagnostico["confianza"] = confidence

        diagnosticos.append(diagnostico)

    return diagnosticos


def medberos_exams_to_consultia(predictions: List[Dict[str, Any]]) -> List[str]:
    """Convierte predicciones de exámenes al formato de Consult-IA."""
    exams = []

    for pred in predictions:
        # Medberos usa "title" para el nombre del examen
        exam_name = pred.get("title") or pred.get("Title") or pred.get("name") or pred.get("Name") or ""
        if exam_name:
            exams.append(exam_name)

    return exams


def medberos_treatments_to_consultia(predictions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convierte predicciones de tratamientos al formato de Consult-IA."""
    tratamientos = []

    for pred in predictions:
        # Medberos usa "title" para nombre de medicamento
        medicamento = pred.get("title") or pred.get("Title") or pred.get("name") or pred.get("Name") or pred.get("MedicineName") or ""

        tratamiento = {
            "medicamento": medicamento,
            "dosisIndicacion": pred.get("Dosage") or pred.get("dosage") or pred.get("Dose") or pred.get("Indication") or ""
        }

        # Agregar código si existe
        code = pred.get("code") or pred.get("Code") or pred.get("GTIN") or pred.get("gtin")
        if code:
            tratamiento["gtin"] = code

        # Medberos no devuelve confianza, usar valor por defecto
        tratamiento["confianza"] = 0.80

        tratamientos.append(tratamiento)

    return tratamientos
