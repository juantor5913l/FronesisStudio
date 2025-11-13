from datetime import datetime
import pytz
import requests
import os
import sys
import traceback
from app.utils.security_utils import encriptar_id

# --- Diccionario de meses en español ---
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

# --- Función para formatear fecha en español ---
def formatear_fecha(fecha_dt):
    dia = fecha_dt.day
    mes = MESES_ES.get(fecha_dt.month, fecha_dt.month)
    año = fecha_dt.year
    return f"{dia} de {mes} de {año}"

# --- Función para formatear hora en 12h ---
def formatear_hora_12h(fecha, hora):
    tz = pytz.timezone("America/Bogota")
    inicio = tz.localize(datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S"))

    hora_24 = inicio.hour
    minuto = inicio.minute
    sufijo = "AM" if hora_24 < 12 else "PM"
    hora_12 = hora_24 % 12 or 12
    hora_formateada = f"{hora_12}:{minuto:02d} {sufijo}"
    fecha_formateada = formatear_fecha(inicio).capitalize()
    return hora_formateada, fecha_formateada


# --- Función para enviar correo vía SendGrid ---
def enviar_por_sendgrid(destinatario, asunto, html_body):
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        print("❌ ERROR: Falta variable SENDGRID_API_KEY en Render.")
        sys.stdout.flush()
        return

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": destinatario}]}],
        "from": {"email": "no-reply@fronesisstudio.com", "name": "Fronesis Studio"},
        "subject": asunto,
        "content": [{"type": "text/html", "value": html_body}]
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    r = requests.post(url, json=payload, headers=headers)
    print("📨 SendGrid status:", r.status_code)
    if r.status_code >= 400:
        print("❌ Error al enviar correo:", r.text)
    else:
        print("✅ Correo enviado correctamente.")
    sys.stdout.flush()


# --- Función principal ---
def enviar_correo_con_invitacion(destinatario, nombre, fecha, hora, tipo, id_cita):
    try:
        # --- Formateo de fecha y hora ---
        if fecha.count('-') == 2 and ':' in hora:
            hora, fecha = formatear_hora_12h(fecha, hora)

        # --- Configuración según el tipo de cita ---
        if tipo == 'nueva':
            asunto = "✅ Confirmación de tu cita en Fronesis Studio"
            titulo = "Confirmación de tu cita"
            descripcion = "Tu cita ha sido agendada exitosamente."
            gradiente = "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
        elif tipo == 'reagendada':
            asunto = "🔄 Tu cita ha sido reagendada"
            titulo = "Tu cita ha sido reagendada"
            descripcion = "Tu cita ha sido actualizada con nueva fecha y hora."
            gradiente = "linear-gradient(90deg,#e67e22,#ff9900,#ffd580)"
        elif tipo == 'cancelada':
            asunto = "❌ Tu cita ha sido cancelada"
            titulo = "Tu cita ha sido cancelada"
            descripcion = "Tu cita fue cancelada correctamente."
            gradiente = "linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b)"
        elif tipo == 'cancelada_admin':
            asunto = "⚠️ Tu cita ha sido cancelada por el barbero"
            titulo = "Cancelación por parte del estudio"
            descripcion = ("Lamentamos informarte que tu cita ha sido cancelada, "
                           "ya que al barbero se le presentó un imprevisto para ese día. "
                           "Puedes reagendar en otro horario disponible.")
            gradiente = "linear-gradient(90deg,#ff8c00,#ff4b2b,#c0392b)"
        elif tipo == 'recordatorio':
            asunto = "⏰ Recordatorio de tu cita - Fronesis Studio"
            titulo = "Recordatorio de tu cita"
            descripcion = "Tu cita se aproxima. Te esperamos en Frónesis Studio dentro de 2 horas."
            gradiente = "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
        else:
            asunto = "📅 Cita en Fronesis Studio"
            titulo = "Detalles de tu cita"
            descripcion = "Detalles de tu cita."
            gradiente = "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"

        # --- Bloque de enlaces ---
        base_url = "https://fronesisstudio.onrender.com"
        enlaces_html = ""
        if tipo != "cancelada":
            token = encriptar_id(id_cita)
            enlaces_html = f"""
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0;">
            <div style="display:flex;justify-content:center;align-items:center;margin-top:20px;">
              <a href='{base_url}/cliente/reagendar/{token}'
                 style="display:inline-block;width:47%;margin-right:6px;padding:1px 1px;font-size:14px;font-weight:700;text-align:center;text-decoration:none;color:#fff;border-radius:8px;background:linear-gradient(90deg,#007bff,#6f00ff,#00c2ff);">
                  <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🔁 Reagendar</span>
              </a>
              <a href='{base_url}/cliente/cancelar_cita/{token}'
                 style="display:inline-block;width:47%;margin-left:6px;padding:1px 1px;font-size:14px;font-weight:700;text-align:center;text-decoration:none;color:#fff;border-radius:8px;background:linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b);">
                  <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🚫 Cancelar</span>
              </a>
            </div>
            """

        # --- Cuerpo HTML ---
        html_body = f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>{asunto}</title></head>
        <body style="font-family:'Poppins',sans-serif;background:#111;color:#fff;text-align:center;">
          <div style="margin:40px auto;max-width:420px;padding:30px;border-radius:18px;background:rgba(255,255,255,0.05);">
            <h2 style="background:{gradiente};-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
              {titulo}, {nombre}
            </h2>
            <p>{descripcion}</p>
            <div style="border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:20px;text-align:left;">
              <p>👤 {nombre}</p>
              <p>⏱ {hora}</p>
              <p>📅 {fecha}</p>
              <p>📍 Carrera 98A #131-05 Aures</p>
              {enlaces_html}
            </div>
          </div>
        </body>
        </html>"""

        # --- Envío vía SendGrid ---
        print("📨 Enviando correo mediante SendGrid...")
        sys.stdout.flush()
        enviar_por_sendgrid(destinatario, asunto, html_body)

    except Exception as e:
        print("❌ ERROR durante el envío del correo:", e)
        traceback.print_exc()
        sys.stdout.flush()
