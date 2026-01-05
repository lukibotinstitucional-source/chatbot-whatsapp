import os
import pandas as pd

# Carpeta donde están los archivos Excel de cursos y docentes
RUTA_DATOS = "datos"

def normalizar_texto(texto):
    """Convierte a minúsculas y elimina espacios y tildes"""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = texto.strip().lower()
    import unicodedata
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return texto

def formatear_cedula(cedula):
    """Asegura que la cédula tenga 10 dígitos con ceros a la izquierda"""
    return str(cedula).strip().zfill(10)

def buscar_cedula(cedula):
    """
    Busca la cédula en todos los archivos Excel dentro de la carpeta 'datos'.
    Retorna un diccionario con información del usuario.
    """
    cedula = formatear_cedula(cedula)
    print(f"\n🟡 Buscando cédula: {cedula}\n")

    for archivo in os.listdir(RUTA_DATOS):
        if archivo.endswith(".xlsx"):
            ruta = os.path.join(RUTA_DATOS, archivo)
            try:
                df = pd.read_excel(ruta, sheet_name=None)
                for hoja, df_hoja in df.items():
                    df_hoja.columns = [col.strip().lower() for col in df_hoja.columns]
                    if "cedula" in df_hoja.columns:
                        df_hoja["cedula"] = df_hoja["cedula"].astype(str).str.strip().str.zfill(10)
                        if cedula in df_hoja["cedula"].values:
                            fila = df_hoja[df_hoja["cedula"] == cedula].iloc[0]
                            nombre = fila["nombre"] if "nombre" in df_hoja.columns else "Desconocido"

                            if "docente" in archivo.lower():
                                return {"rol": "docente", "nombre": nombre, "curso": "Docentes", "archivo": archivo}
                            else:
                                curso = fila["curso"] if "curso" in df_hoja.columns else archivo.replace(".xlsx", "")
                                return {"rol": "estudiante", "nombre": nombre, "curso": curso, "archivo": archivo}
            except Exception as e:
                print(f"❌ Error leyendo {archivo}: {e}")
    print("🚫 Cédula no encontrada en ningún archivo.")
    return None

def obtener_datos_hoja(archivo, hoja, cedula=None):
    """
    Abre un archivo Excel y devuelve los datos de una hoja específica.
    Si se pasa 'cedula', filtra solo la fila correspondiente.
    """
    ruta = os.path.join(RUTA_DATOS, archivo)
    try:
        df = pd.read_excel(ruta, sheet_name=hoja)
        df.columns = [col.strip().lower() for col in df.columns]

        if cedula and "cedula" in df.columns:
            df["cedula"] = df["cedula"].astype(str).str.strip().str.zfill(10)
            df = df[df["cedula"] == formatear_cedula(cedula)]

        return df
    except Exception as e:
        print(f"❌ Error leyendo hoja '{hoja}' en '{archivo}': {e}")
        return pd.DataFrame()
