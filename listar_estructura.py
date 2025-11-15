import os

def listar_estructura(base_path, file_out, nivel=0):
    """Lista recursivamente la estructura de carpetas y archivos y la escribe en un archivo."""
    prefijo = "    " * nivel + "|-- "
    try:
        items = sorted(os.listdir(base_path))
    except PermissionError:
        file_out.write(prefijo + "[Permiso denegado]\n")
        return

    for item in items:
        ruta = os.path.join(base_path, item)
        if os.path.isdir(ruta):
            file_out.write(prefijo + f"[{item}]\n")
            listar_estructura(ruta, file_out, nivel + 1)
        else:
            file_out.write(prefijo + item + "\n")

if __name__ == "__main__":
    # Ruta de la carpeta donde descomprimiste consultia.rar
    ruta_base = "consultia"   # cámbiala si la extrajiste en otro directorio
    archivo_salida = "estructura.txt"

    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(f"Estructura del proyecto en: {ruta_base}\n\n")
        listar_estructura(ruta_base, f)

    print(f"Estructura generada en {archivo_salida}")
