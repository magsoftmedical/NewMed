#!/usr/bin/env python3
"""Test super simple de streaming"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = os.getenv("OPENAI_MODEL_TEXT", "gpt-3.5-turbo")

print(f"Modelo: {model}")
print("Iniciando streaming...")
print("-" * 60)

start = time.time()

try:
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Cuenta del 1 al 10"}
        ],
        temperature=1.0,
        stream=True
    )

    token_count = 0
    for chunk in stream:
        elapsed = time.time() - start
        delta = chunk.choices[0].delta.get("content")
        if delta:
            token_count += 1
            print(f"[{elapsed:.2f}s] Token #{token_count}: {repr(delta)}")

    print("-" * 60)
    print(f"Total: {token_count} tokens en {time.time() - start:.2f}s")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
