
import os

# Carpetas a excluir
EXCLUDE = {'.git', '.venv', '__pycache__', 'node_modules', '.angular', 'dist', 'build'}

def should_skip(path):
    return any(part in EXCLUDE for part in path.split(os.sep))

with open("estructura.txt", "w", encoding="utf-8") as f:
    for dirpath, dirnames, filenames in os.walk("."):
        if should_skip(dirpath):
            continue
        level = dirpath.count(os.sep)
        indent = " " * 2 * level
        f.write(f"{indent}{os.path.basename(dirpath)}/\n")
        subindent = " " * 2 * (level + 1)
        for name in sorted(filenames):
            if should_skip(name):
                continue
            f.write(f"{subindent}{name}\n")

print("✅ Archivo 'estructura.txt' generado con la estructura de carpetas.")
