from datetime import datetime, timedelta
import json
import os
from openpyxl import load_workbook
from lector_excel import buscar_cedula
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# 🚀 Flask app
app = Flask(__name__)

# 🧩 Sesiones por usuario (multiusuario)
sesiones = {}

# 📘 Cargar menú desde JSON
def cargar_menu():
    with open("menu.json", "r", encoding="utf-8") as f:
        return json.load(f)

menu = cargar_menu()

# 📁 Carpeta de archivos TXT
RUTA_TXT = "txt"

# 🔹 Mostrar menú principal
def mostrar_menu_principal():
    texto = "\n📋 *MENÚ PRINCIPAL*\n"
    for clave, item in menu.items():
        texto += f"{clave}. {item['titulo']}\n"
    texto += "\n➡️ Responde con el número de tu elección:"
    return texto

# 🔹 Mostrar submenú
def mostrar_submenu(opcion):
    sub = menu[opcion]["subopciones"]
    texto = f"\n📂 *{menu[opcion]['titulo']}*\n"
    for clave, item in sub.items():
        texto += f"{clave}. {item}\n"
    texto += "\n⬅️ Escribe 0 para volver al menú principal."
    return texto

# 🔹 Leer archivo TXT
def leer_txt(nombre_archivo):
    ruta = os.path.join(RUTA_TXT, f"{nombre_archivo}.txt")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "❌ Archivo de información no encontrado."

# 🔹 Limpieza automática de sesiones
def limpiar_sesiones():
    ahora = datetime.now()
    for uid in list(sesiones.keys()):
        ultimo = sesiones[uid].get("ultimo")
        if ultimo and (ahora - ultimo > timedelta(minutes=30)):
            del sesiones[uid]

# 🔹 Funciones Excel
def obtener_horario(usuario):
    archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
    if not os.path.exists(archivo):
        return f"❌ No se encontró el archivo del curso: {usuario.get('curso', '')}"
    try:
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Horario"]
        contenido = ""
        for row in ws.iter_rows(values_only=True):
            fila = [str(celda) for celda in row if celda]
            if fila:
                contenido += " | ".join(fila) + "\n"
        return f"🕒 *Horario del curso {usuario['curso']}*\n{contenido}"
    except Exception as e:
        return f"❌ Error al obtener horario: {str(e)}"

def obtener_horario_docente(usuario):
    try:
        archivo = os.path.join("datos", "docentes.xlsx")
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Horario"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, link = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                return f"🕒 *Horario del Docente*\n{link}"
        return "❌ No se encontró horario asignado."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def obtener_materias_docente(usuario):
    try:
        archivo = os.path.join("datos", "docentes.xlsx")
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Materias"]
        materias = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, materia = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                materias.append(str(materia))
        return "📚 *Materias que dictas:*\n- " + "\n- ".join(materias)
    except Exception as e:
        return f"❌ Error: {str(e)}"

def obtener_claves(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("archivo", ""))
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Claves"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, usuario_plat, clave = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                return f"🔐 *Acceso*\n👤 Usuario: {usuario_plat}\n🔑 Contraseña: {clave}"
        return "❌ No se encontraron credenciales."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def obtener_materias(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Materias"]
        materias = [str(row[0]) for row in ws.iter_rows(values_only=True) if row[0]]
        return "📚 *Materias:*\n- " + "\n- ".join(materias)
    except Exception as e:
        return f"❌ Error: {str(e)}"

def obtener_profesores(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Profesores"]
        profesores = [str(row[0]) for row in ws.iter_rows(values_only=True) if row[0]]
        return "👨‍🏫 *Profesores:*\n- " + "\n- ".join(profesores)
    except Exception as e:
        return f"❌ Error: {str(e)}"

def obtener_valores_pendientes(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("archivo", ""))
        wb = load_workbook(filename=archivo, data_only=True)
        ws = wb["Pagos"]
        pendientes = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, mes, monto = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                pendientes.append(f"- {mes}: ${monto}")
        return "💰 *Valores pendientes:*\n" + "\n".join(pendientes) if pendientes else "✅ No tienes valores pendientes."
    except Exception as e:
        return f"❌ Error: {str(e)}"

# 🔹 Procesar mensajes (multiusuario real)
def procesar_mensaje_multiusuario(mensaje, sesion):
    ahora = datetime.now()

    # 🚪 Salir en cualquier momento
    if mensaje in ["salir", "exit", "cancelar"]:
        sesion.update({
            "usuario": {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None},
            "nivel": "menu_principal",
            "opcion": None,
            "ultimo": ahora
        })
        return "🔄 Sesión reiniciada.\n👋 Ingresa tu número de cédula."

    usuario = sesion["usuario"]

    # ⏰ Inactividad
    if sesion.get("ultimo") and (ahora - sesion["ultimo"] > timedelta(minutes=10)):
        sesion.update({
            "usuario": {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None},
            "nivel": "menu_principal",
            "opcion": None
        })
        return "⏰ Sesión cerrada por inactividad.\nIngresa tu cédula."

    sesion["ultimo"] = ahora

    # 🔐 Cédula
    if usuario["rol"] is None:
        if mensaje.isdigit() and len(mensaje) >= 10:
            info = buscar_cedula(mensaje)
            if info:
                info["cedula"] = mensaje
                info["archivo"] = info.get("curso", "") + ".xlsx"
                sesion["usuario"] = info
                sesion["nivel"] = "menu_principal"
                return f"✅ Bienvenido {info['nombre']}.\n" + mostrar_menu_principal()
            return "⚠ Cédula no encontrada."
        return "👋 Ingresa tu número de cédula."

    # 📋 Menú
    if sesion["nivel"] == "menu_principal":
        if mensaje in menu:
            sesion["nivel"] = "submenu"
            sesion["opcion"] = mensaje
            return mostrar_submenu(mensaje)
        return "⚠ Opción no válida."

    if sesion["nivel"] == "submenu":
        if mensaje == "0":
            sesion["nivel"] = "menu_principal"
            return mostrar_menu_principal()

        opcion = menu[sesion["opcion"]]["subopciones"].get(mensaje, "").lower()

        if "horario" in opcion:
            return obtener_horario_docente(usuario) if usuario["rol"] == "docente" else obtener_horario(usuario)
        if "materias" in opcion:
            return obtener_materias_docente(usuario) if usuario["rol"] == "docente" else obtener_materias(usuario)
        if "profesores" in opcion:
            return obtener_profesores(usuario)
        if "plataforma" in opcion:
            return obtener_claves(usuario)
        if "valores" in opcion:
            return obtener_valores_pendientes(usuario)

        return leer_txt(opcion)

    return "❓ No entendí tu mensaje."

# 🔹 Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    limpiar_sesiones()

    mensaje = request.form.get("Body", "").strip().lower()
    usuario_id = request.form.get("From")

    if usuario_id not in sesiones:
        sesiones[usuario_id] = {
            "usuario": {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None},
            "nivel": "menu_principal",
            "opcion": None,
            "ultimo": None
        }

    respuesta = procesar_mensaje_multiusuario(mensaje, sesiones[usuario_id])

    resp = MessagingResponse()
    resp.message(respuesta)
    return str(resp)

@app.route("/")
def home():
    return "Servidor Flask activo ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
