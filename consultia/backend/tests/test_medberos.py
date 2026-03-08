"""
Script de prueba para verificar la integración con Medberos AI.

Ejecutar:
    python test_medberos.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Allow running as standalone script from tests/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.medberos import medberos_client, consultia_to_medberos_payload


async def test_authentication():
    """Prueba la autenticación con Medberos."""
    print("=" * 60)
    print("TEST 1: Autenticación")
    print("=" * 60)

    result = await medberos_client.test_connection()

    if result.get("ok"):
        print("✅ Autenticación exitosa")
        print(f"   Mensaje: {result.get('message')}")
    else:
        print("❌ Error de autenticación")
        print(f"   Error: {result.get('error')}")

    print()
    return result.get("ok")


async def test_predict_diagnoses():
    """Prueba la predicción de diagnósticos."""
    print("=" * 60)
    print("TEST 2: Predicción de Diagnósticos")
    print("=" * 60)

    # Formulario de ejemplo
    form = {
        "afiliacion": {
            "edad": {"anios": 35},
            "sexo": "F",
            "grupoSangre": "O+"
        },
        "anamnesis": {
            "sintomasPrincipales": ["fiebre", "tos seca", "dolor de cabeza"],
            "tiempoEnfermedad": "3 días"
        },
        "examenClinico": {
            "signosVitales": {
                "temperatura": "38.5",
                "PA": "120/80",
                "FC": 88
            }
        }
    }

    doctor_comments = "Paciente refiere cuadro gripal. Posible infección viral respiratoria."

    # Convertir al formato de Medberos
    payload = consultia_to_medberos_payload(form, doctor_comments)

    print("📤 Enviando payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    # Llamar a Medberos
    result = await medberos_client.predict_diagnoses(payload)

    if "error" not in result:
        print("✅ Predicción exitosa")
        predictions = result.get("predictions", [])
        print(f"   Recibidas {len(predictions)} predicciones:")

        for i, pred in enumerate(predictions[:5], 1):  # Mostrar máximo 5
            print(f"\n   📋 Predicción {i} (RAW):")
            print(f"      {json.dumps(pred, indent=6, ensure_ascii=False)}")
            print(f"      Keys: {list(pred.keys())}")
            name = pred.get("Name", "N/A")
            icd10 = pred.get("ICD10Code", "N/A")
            confidence = pred.get("Confidence", 0)
            print(f"   {i}. {name} ({icd10}) - Confianza: {confidence:.2%}")
    else:
        print("❌ Error en predicción")
        print(f"   Error: {result.get('error')}")

    print()
    return "error" not in result


async def test_predict_exams():
    """Prueba la predicción de exámenes."""
    print("=" * 60)
    print("TEST 3: Predicción de Exámenes")
    print("=" * 60)

    form = {
        "afiliacion": {
            "edad": {"anios": 35},
            "sexo": "F"
        },
        "anamnesis": {
            "sintomasPrincipales": ["fiebre", "tos"]
        },
        "diagnosticos": [
            {"nombre": "Infección respiratoria aguda", "cie10": "J06.9", "tipo": "Presuntivo"}
        ]
    }

    doctor_comments = "Solicitar exámenes para descartar infección bacteriana."

    payload = consultia_to_medberos_payload(form, doctor_comments)

    result = await medberos_client.predict_exams(payload)

    if "error" not in result:
        print("✅ Predicción exitosa")
        predictions = result.get("predictions", [])
        print(f"   Recibidas {len(predictions)} predicciones de exámenes:")

        for i, pred in enumerate(predictions[:5], 1):
            name = pred.get("Name", "N/A")
            print(f"   {i}. {name}")
    else:
        print("❌ Error en predicción")
        print(f"   Error: {result.get('error')}")

    print()
    return "error" not in result


async def test_predict_treatments():
    """Prueba la predicción de tratamientos."""
    print("=" * 60)
    print("TEST 4: Predicción de Tratamientos")
    print("=" * 60)

    form = {
        "afiliacion": {
            "edad": {"anios": 35},
            "sexo": "F"
        },
        "anamnesis": {
            "sintomasPrincipales": ["fiebre", "dolor de cabeza"]
        },
        "diagnosticos": [
            {"nombre": "Gripe", "cie10": "J11.1", "tipo": "Presuntivo"}
        ]
    }

    doctor_comments = "Iniciar tratamiento sintomático. Sin alergias conocidas."

    payload = consultia_to_medberos_payload(form, doctor_comments)

    result = await medberos_client.predict_treatments(payload)

    if "error" not in result:
        print("✅ Predicción exitosa")
        predictions = result.get("predictions", [])
        print(f"   Recibidas {len(predictions)} predicciones de tratamientos:")

        for i, pred in enumerate(predictions[:5], 1):
            name = pred.get("Name", "N/A")
            dosage = pred.get("Dosage", "N/A")
            print(f"   {i}. {name} - {dosage}")
    else:
        print("❌ Error en predicción")
        print(f"   Error: {result.get('error')}")

    print()
    return "error" not in result


async def main():
    """Ejecuta todos los tests."""
    print("\n🔬 MEDBEROS AI - TESTS DE INTEGRACIÓN\n")

    results = []

    # Test 1: Autenticación
    results.append(await test_authentication())

    if not results[0]:
        print("⚠️  No se puede continuar sin autenticación válida.")
        print("\n📝 Verifica que hayas configurado MEDBEROS_API_KEY y MEDBEROS_API_SECRET en .env")
        return

    # Test 2: Predicción de diagnósticos
    results.append(await test_predict_diagnoses())

    # Test 3: Predicción de exámenes
    results.append(await test_predict_exams())

    # Test 4: Predicción de tratamientos
    results.append(await test_predict_treatments())

    # Resumen
    print("=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"✅ Pasados: {passed}/{total}")
    print(f"❌ Fallidos: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron exitosamente!")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisa los logs arriba.")

    # Cerrar cliente
    await medberos_client.close()


if __name__ == "__main__":
    asyncio.run(main())
