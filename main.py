from datetime import datetime, timedelta
import json
import os
from openpyxl import load_workbook
from lector_excel import buscar_cedula
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# 🧩 Variables globales
usuario_actual = {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None}
nivel_actual = "menu_principal"
opcion_actual = None
ultimo_mensaje = None

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

# 🔹 Obtener horario (hoja “Horario” de curso)
def obtener_horario(usuario):
    archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
    if not os.path.exists(archivo):
        return f"❌ No se encontró el archivo del curso: {usuario.get('curso', '')}"
    try:
        wb = load_workbook(filename=archivo, data_only=True)
        if "Horario" not in wb.sheetnames:
            return "❌ Hoja 'Horario' no encontrada en el archivo."
        ws = wb["Horario"]
        contenido = ""
        for row in ws.iter_rows(values_only=True):
            fila = [str(celda) for celda in row if celda]
            if fila:
                contenido += " | ".join(fila) + "\n"
        return f"🕒 *Horario del curso {usuario['curso']}*\n{contenido}" if contenido else "❌ No se encontró horario para este curso."
    except Exception as e:
        return f"❌ Error al obtener horario: {str(e)}"

# 🔹 Obtener horario docente (docentes.xlsx)
def obtener_horario_docente(usuario):
    try:
        archivo = os.path.join("datos", "docentes.xlsx")
        if not os.path.exists(archivo):
            return "❌ Archivo de docentes no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Horario" not in wb.sheetnames:
            return "❌ Hoja 'Horario' no encontrada."
        ws = wb["Horario"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, link = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                return f"🕒 *Horario del Docente*\n{link}"
        return "❌ No se encontró horario asignado para tu cédula."
    except Exception as e:
        return f"❌ Error al obtener horario: {str(e)}"

# 🔹 Obtener materias del docente (docentes.xlsx)
def obtener_materias_docente(usuario):
    try:
        archivo = os.path.join("datos", "docentes.xlsx")
        if not os.path.exists(archivo):
            return "❌ Archivo de docentes no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Materias" not in wb.sheetnames:
            return "❌ Hoja 'Materias' no encontrada."
        ws = wb["Materias"]
        materias = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, materia = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip() and materia:
                materias.append(str(materia))
        return "📚 *Materias que dictas:*\n- " + "\n- ".join(materias) if materias else "❌ No se encontraron materias asignadas a tu cédula."
    except Exception as e:
        return f"❌ Error al obtener materias: {str(e)}"

# 🔹 Obtener claves de plataforma (hoja “Claves”)
def obtener_claves(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("archivo", ""))
        if not os.path.exists(archivo):
            return "❌ Archivo del curso no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Claves" not in wb.sheetnames:
            return "❌ Hoja 'Claves' no encontrada en el archivo."
        ws = wb["Claves"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, *resto = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                if len(resto) == 1:
                    contraseña = resto[0]
                    return f"🔐 *Acceso a la plataforma educativa*\n👤 Cédula: {cedula_excel}\n🔑 Contraseña: {contraseña}"
                elif len(resto) >= 2:
                    usuario_plat, contraseña = resto[:2]
                    return f"🔐 *Acceso a la plataforma educativa*\n👤 Usuario: {usuario_plat}\n🔑 Contraseña: {contraseña}"
        return "❌ No se encontraron credenciales para esta cédula."
    except Exception as e:
        return f"❌ Error al obtener las claves: {str(e)}"

# 🔹 Obtener materias del curso (hoja “Materias”)
def obtener_materias(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
        if not os.path.exists(archivo):
            return "❌ Archivo del curso no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Materias" not in wb.sheetnames:
            return "❌ Hoja 'Materias' no encontrada en el archivo."
        ws = wb["Materias"]
        materias = [str(row[0]) for row in ws.iter_rows(values_only=True) if row[0]]
        return "📚 *Materias del curso {}*:\n- ".format(usuario["curso"]) + "\n- ".join(materias) if materias else "❌ No se encontraron materias."
    except Exception as e:
        return f"❌ Error al obtener materias: {str(e)}"

# 🔹 Obtener profesores del curso (hoja “Profesores”)
def obtener_profesores(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("curso", "").strip() + ".xlsx")
        if not os.path.exists(archivo):
            return "❌ Archivo del curso no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Profesores" not in wb.sheetnames:
            return "❌ Hoja 'Profesores' no encontrada en el archivo."
        ws = wb["Profesores"]
        profesores = [str(row[0]) for row in ws.iter_rows(values_only=True) if row[0]]
        return "👨‍🏫 *Profesores del curso {}*:\n- ".format(usuario["curso"]) + "\n- ".join(profesores) if profesores else "❌ No se encontraron profesores."
    except Exception as e:
        return f"❌ Error al obtener profesores: {str(e)}"

# 🔹 Obtener valores pendientes (hoja “Pagos”)
def obtener_valores_pendientes(usuario):
    try:
        archivo = os.path.join("datos", usuario.get("archivo", ""))
        if not os.path.exists(archivo):
            return "❌ Archivo del curso no encontrado."
        wb = load_workbook(filename=archivo, data_only=True)
        if "Pagos" not in wb.sheetnames:
            return "❌ Hoja 'Pagos' no encontrada en el archivo."
        ws = wb["Pagos"]

        pendientes = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            cedula_excel, mes, monto = row
            if str(cedula_excel).strip() == str(usuario["cedula"]).strip():
                pendientes.append((mes, monto))

        if not pendientes:
            return "✅ No tienes valores pendientes."

        mensaje = f"💰 *Valores pendientes para {usuario['nombre']}*:\n"
        for mes, monto in pendientes:
            mensaje += f"- {mes}: ${monto}\n"
        return mensaje

    except Exception as e:
        return f"❌ Error al obtener valores pendientes: {str(e)}"

# 🔹 Procesar mensajes
def procesar_mensaje(mensaje):
    global nivel_actual, opcion_actual, usuario_actual, ultimo_mensaje
    mensaje = mensaje.strip().lower()
    ahora = datetime.now()

    # 🔸 Verificar si ha pasado más de 10 minutos sin actividad
    if ultimo_mensaje and (ahora - ultimo_mensaje > timedelta(minutes=10)):
        usuario_actual = {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None}
        nivel_actual = None
        opcion_actual = None
        ultimo_mensaje = None
        return ("⏰ La sesión se ha cerrado automáticamente por inactividad.\n\n"
                "👋 ¡Hola! Soy *Lukibot*, el asistente virtual de la *Unidad Educativa María Luisa Luque de Sotomayor*.\n"
                "Por favor ingresa tu número de cédula para continuar.")

    # 🔸 Actualizar el tiempo del último mensaje
    ultimo_mensaje = ahora

    if usuario_actual["rol"] is None:
        if mensaje.isdigit() and len(mensaje) >= 10:
            info = buscar_cedula(mensaje)
            if info:
                info["archivo"] = info.get("curso", "").strip() + ".xlsx"
                info["cedula"] = mensaje
                usuario_actual = info
                rol = info["rol"].upper()
                return f"✅ Bienvenido {info['nombre']}. Has ingresado como *{rol}*.\n" + mostrar_menu_principal()
            else:
                return "⚠ Cédula no encontrada. Verifica tu número e intenta nuevamente."
        else:
            return ("👋 ¡Hola! Soy *Lukibot*, el asistente virtual de la *Unidad Educativa María Luisa Luque de Sotomayor*.\n"
                    "Estoy aquí para ayudarte con información y servicios educativos.\n\n"
                    "Por favor ingresa tu número de cédula (solo números).")

    if nivel_actual == "menu_principal":
        if mensaje.isdigit():
            if mensaje == "0":
                return mostrar_menu_principal()
            if mensaje in menu:
                opcion_actual = mensaje
                nivel_actual = "submenu"
                return mostrar_submenu(mensaje)
            else:
                return "⚠ Opción no válida. Intenta de nuevo."
        else:
            return "Por favor responde con el número de la opción."

    elif nivel_actual == "submenu":
        if mensaje == "0":
            nivel_actual = "menu_principal"
            return mostrar_menu_principal()

        sub = menu[opcion_actual]["subopciones"]
        if mensaje in sub:
            opcion_texto = sub[mensaje]
            if opcion_actual == "10" and mensaje == "1":
                usuario_actual = {"rol": None, "nombre": None, "curso": None, "archivo": None, "cedula": None}
                nivel_actual = "menu_principal"
                opcion_actual = None
                return "🔄 Sesión finalizada. Por favor ingresa tu número de cédula para iniciar nuevamente."

            if usuario_actual["rol"] == "estudiante" and opcion_texto in [
                "Solicitar claves del Wi-Fi institucional",
                "Reglamento interno para docentes"
            ]:
                return "🚫 No tienes permiso para acceder a esta opción."

            if usuario_actual["rol"] == "docente":
                if "horario" in opcion_texto.lower():
                    return obtener_horario_docente(usuario_actual)
                if "materias" in opcion_texto.lower():
                    return obtener_materias_docente(usuario_actual)
                if "profesores" in opcion_texto.lower() and "curso" in opcion_texto.lower():
                    return "👨‍🏫 Estimado docente, esta opción está restringida para tu rol."

            if "plataforma educativa" in opcion_texto.lower():
                return obtener_claves(usuario_actual)
            if opcion_texto.lower() == "horario de atención a padres":
                return leer_txt("Horario de atencion a padres")
            if opcion_texto.lower() == "horario de recuperación o supletorios":
                return leer_txt("Horario de recuperacion o supletorios")
            if "horario" in opcion_texto.lower():
                return obtener_horario(usuario_actual)
            if "materias" in opcion_texto.lower():
                return obtener_materias(usuario_actual)
            if "profesores" in opcion_texto.lower() and "curso" in opcion_texto.lower():
                return obtener_profesores(usuario_actual)
            if "valores pendientes" in opcion_texto.lower():
                if usuario_actual["rol"] == "docente":
                    return "🚫 Estimado docente, esta opción no está disponible para su rol."
                else:
                    return obtener_valores_pendientes(usuario_actual)
            if "profesores" in opcion_texto.lower() and "nivel" in opcion_texto.lower():
                return leer_txt(opcion_texto)
            txt = leer_txt(opcion_texto)
            if txt != "❌ Archivo de información no encontrado.":
                return txt
            return f"📄 Has seleccionado: *{opcion_texto}*"
        else:
            return "⚠ Opción no válida. Intenta de nuevo."
    return "❓ No entendí tu mensaje."

# 🚀 --- CONEXIÓN A TWILIO (WHATSAPP) ---
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    response_text = procesar_mensaje(incoming_msg)
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(response_text)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Servidor Flask activo ✅ Usa /webhook para mensajes de WhatsApp."

if __name__ == "__main__":
    print("✅ Servidor Flask ejecutándose en http://localhost:5000 ...")
    app.run(port=5000)
