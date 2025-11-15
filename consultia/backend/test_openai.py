#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que OpenAI funciona correctamente.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini")

print("=" * 60)
print("TEST DE CONEXIÓN A OPENAI")
print("=" * 60)
print()

# Verificar API key
if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY no está definida en .env")
    exit(1)

print(f"✓ API Key encontrada: {OPENAI_API_KEY[:20]}...")
print(f"✓ Modelo: {OPENAI_MODEL_TEXT}")
print()

# Crear cliente
client = OpenAI(api_key=OPENAI_API_KEY)

# Test 1: Llamada simple sin streaming
print("-" * 60)
print("TEST 1: Llamada simple (sin streaming)")
print("-" * 60)

try:
    response = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "user", "content": "Di solo 'hola'"}
        ],
        temperature=0
    )

    content = response.choices[0].message.content
    print(f"✓ Respuesta recibida: {content}")
    print()
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 2: Llamada con streaming
print("-" * 60)
print("TEST 2: Llamada con streaming (como en el sistema)")
print("-" * 60)

transcript = "Paciente viene por fiebre desde hace dos días"

# TEST A: Prompt SIMPLE (sin campos faltantes)
system_simple = "Eres un asistente médico. Resume brevemente el caso."

# TEST B: Prompt con campos faltantes
missing = ["motivo de consulta", "síntomas principales", "diagnósticos", "plan de tratamiento"]
system_parts = [
    "Eres un asistente clínico inteligente. Resume en 2-4 líneas lo más relevante del caso: "
    "motivo de consulta, síntomas clave, hallazgos importantes."
]

if missing:
    missing_text = ", ".join(missing)
    system_parts.append(f" Al final menciona brevemente que falta registrar: {missing_text}.")

system_parts.append(" Mantén tono profesional. No inventes datos.")

system_complex = "".join(system_parts)

# Probar primero el SIMPLE
system = system_simple
user_content = transcript

print(f"System prompt: {system}")
print(f"User content: {user_content}")

print(f"Prompt: {transcript}")
print()
print("Respuesta en streaming:")
print("-" * 60)

try:
    stream = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content}
        ],
        temperature=0.2,
        stream=True
    )

    full_response = ""
    token_count = 0

    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.get("content")
        except Exception:
            delta = None

        if delta:
            token_count += 1
            full_response += delta
            print(delta, end="", flush=True)

    print()
    print()
    print(f"✓ Streaming completado: {token_count} tokens recibidos")
    print(f"✓ Respuesta completa: {full_response}")
    print()

except Exception as e:
    print(f"❌ Error en streaming: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Extracción JSON
print("-" * 60)
print("TEST 3: Extracción JSON (como extract_form_delta)")
print("-" * 60)

try:
    response = client.chat.completions.create(
        model=OPENAI_MODEL_TEXT,
        messages=[
            {
                "role": "user",
                "content": "Extrae de este texto: 'paciente viene por fiebre'. Devuelve JSON: {\"motivoConsulta\": \"...\"}"
            }
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    print(f"✓ JSON recibido: {content}")
    print()

except Exception as e:
    print(f"❌ Error en JSON: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
print("TODOS LOS TESTS COMPLETADOS")
print("=" * 60)
print()
print("Si todos los tests pasaron, OpenAI está funcionando correctamente.")
print("El problema está en el frontend o en la conexión WebSocket.")
