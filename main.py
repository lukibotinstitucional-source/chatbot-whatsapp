from datetime import datetime, timedelta
import json
import os
from openpyxl import load_workbook
from lector_excel import buscar_cedula
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

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

# 🔹 (TODAS tus funciones de Excel se mantienen IGUAL)
# obtener_horario, obtener_horario_docente, obtener_materias_docente,
# obtener_claves, obtener_materias, obtener_profesores, obtener_valores_pendientes
# ⬆️ NO SE TOCAN (las dejo iguales para no alargar el mensaje)

# 🔹 Procesar mensajes (MULTIUSUARIO)
def procesar_mensaje(mensaje, sesion):
    mensaje = mensaje.strip().lower()
    ahora = datetime.now()

    # ⏰ Expiración por inactividad
    if sesion["ultimo"] and (ahora - sesion["ultimo"] > timedelta(minutes=10)):
        sesion.update({
            "usuario": {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None},
            "nivel": "menu_principal",
            "opcion": None,
            "ultimo": ahora
        })
        return (
            "⏰ La sesión se cerró por inactividad.\n\n"
            "👋 ¡Hola! Soy *Lukibot*, el asistente virtual de la *Unidad Educativa María Luisa Luque de Sotomayor*.\n"
            "Por favor ingresa tu número de cédula."
        )

    sesion["ultimo"] = ahora
    usuario = sesion["usuario"]

    # 🔐 Inicio / cédula
    if usuario["rol"] is None:
        if mensaje.isdigit() and len(mensaje) >= 10:
            info = buscar_cedula(mensaje)
            if info:
                info["archivo"] = info.get("curso", "").strip() + ".xlsx"
                info["cedula"] = mensaje
                sesion["usuario"] = info
                return f"✅ Bienvenido {info['nombre']}.\n" + mostrar_menu_principal()
            return "⚠ Cédula no encontrada."
        return (
            "👋 ¡Hola! Soy *Lukibot*.\n"
            "Por favor ingresa tu número de cédula (solo números)."
        )

    # 📋 Menú principal
    if sesion["nivel"] == "menu_principal":
        if mensaje in menu:
            sesion["opcion"] = mensaje
            sesion["nivel"] = "submenu"
            return mostrar_submenu(mensaje)
        return "⚠ Opción no válida."

    # 📂 Submenú
    if sesion["nivel"] == "submenu":
        if mensaje == "0":
            sesion["nivel"] = "menu_principal"
            return mostrar_menu_principal()

        sub = menu[sesion["opcion"]]["subopciones"]
        if mensaje in sub:
            return f"📄 Has seleccionado: *{sub[mensaje]}*"

    return "❓ No entendí tu mensaje."

# 🚀 --- FLASK + TWILIO ---
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Servidor Flask activo ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    print("📩 Webhook llamado correctamente")
    incoming_msg = request.values.get("Body", "SIN MENSAJE")

    resp = MessagingResponse()
    resp.message(f"Mensaje recibido: {incoming_msg}")
    return str(resp)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
    
