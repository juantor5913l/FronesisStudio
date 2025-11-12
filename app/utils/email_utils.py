from flask_mail import Message
from datetime import datetime
import pytz
from email.mime.image import MIMEImage
from app import mail
from app.utils.security_utils import encriptar_id

# 🔹 Diccionario de meses en español
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

# --- FUNCIÓN PARA FORMATEAR FECHA EN ESPAÑOL ---
def formatear_fecha(fecha_dt):
    dia = fecha_dt.day
    mes = MESES_ES.get(fecha_dt.month, fecha_dt.month)
    año = fecha_dt.year
    return f"{dia} de {mes} de {año}"

# --- FUNCIÓN PARA FORMATEAR HORA EN 12H ---
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

# --- FUNCIÓN PRINCIPAL DE ENVÍO ---
def enviar_correo_con_invitacion(destinatario, nombre, fecha, hora, tipo, id_cita):
    if fecha.count('-') == 2 and ':' in hora:
        hora, fecha = formatear_hora_12h(fecha, hora)

    # --- CONFIGURACIÓN SEGÚN EL TIPO DE CITA ---
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
    
    # --- BLOQUE DE ENLACES ESTILO FRONESIS ---
    base_url = "http://192.168.20.28:5000"
    enlaces_html = ""
    if tipo != "cancelada":
        token = encriptar_id(id_cita)
        enlaces_html = f"""
        <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0;">
        <div style="display:flex;justify-content:center;align-items:center;margin-top:20px;">

          <!-- BOTÓN REAGENDAR -->
          <a href='{base_url}/cliente/reagendar/{token}'
             style="display:inline-block;width:47%;margin-right:6px;padding:1px 1px;font-size:14px;font-weight:700;letter-spacing:0.3px;text-align:center;text-decoration:none;color:#fff;border-radius:8px;background:linear-gradient(90deg,#007bff,#6f00ff,#00c2ff);position:relative;z-index:1;">
              <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🔁 Reagendar</span>
          </a>

          <!-- BOTÓN CANCELAR -->
          <a href='{base_url}/cliente/cancelar_cita/{token}'
             style="display:inline-block;width:47%;margin-left:6px;padding:1px 1px;font-size:14px;font-weight:700;letter-spacing:0.3px;text-align:center;text-decoration:none;color:#fff;border-radius:8px;background:linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b);position:relative;z-index:1;">
              <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🚫 Cancelar</span>
          </a>
        </div>
        """

    # --- HTML DEL CORREO ---
    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{asunto}</title>
  <style>
    a, a:link, a:visited, a span, p span, td span {{
      color: #ffffff !important;
      text-decoration: none !important;
    }}
    span, p, div, td {{
      color: #ffffff !important;
    }}
    @media (max-width:480px) {{
      .boton-responsive {{
        display:block !important;
        width:100% !important;
        margin:8px 0 !important;
      }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;font-family:'Poppins',sans-serif;background:linear-gradient(135deg,rgba(15,15,15,0.95),rgba(25,25,25,0.98));color:#ffffff !important;text-align:center;">
  <div style="margin:40px auto;max-width:420px;width:92%;border-radius:18px;background:rgba(255,255,255,0.05);box-shadow:0 4px 25px rgba(0,0,0,0.5);padding:30px 22px;">
    <table role="presentation" width="90" height="90" align="center" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;border-radius:50%;background:{gradiente};margin:0 auto 20px auto;">
      <tr>
        <td align="center" valign="middle" style="border-radius:50%;background:#0f0f0f;padding:3px;">
          <img src="cid:logo_fronesis" alt="Logo Fronesis" width="84" height="84" style="border-radius:50%;display:block;">
        </td>
      </tr>
    </table>
    <h2 style="font-size:22px;font-weight:600;margin:0 0 10px 0;background:{gradiente};-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">
      {titulo}, {nombre}
    </h2>
    <p style="color:#ffffff;font-size:14px;margin:0 0 25px 0;">{descripcion}</p>
    <div style="border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:20px;text-align:left;color:#ffffff !important;">
      <h3 style="text-align:center;font-size:17px;margin:0 0 14px 0;background:{gradiente};-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">
        Reserva Estudio<br>
        <span style="font-weight:800;font-size:19px;">FRONESIS</span>
      </h3>
      <p style="font-size:14px;margin:10px 0;">👤 {nombre}</p>
      <p style="font-size:14px;margin:10px 0;">⏱ {hora}</p>
      <p style="font-size:14px;margin:10px 0;">📅 {fecha}</p>
      <p style="font-size:14px;margin:10px 0;">📍 Carerra 98A #131-05 Aures</p>
      <br>
      {enlaces_html}
    </div>
  </div>
</body>
</html>
"""

    # --- CREAR MENSAJE ---
    msg = Message(
        subject=asunto,
        sender=("Fronesis Studio", "tu_correo@gmail.com"),
        recipients=[destinatario],
        html=html_body
    )

    # --- INCRUSTAR LOGO INLINE ---
    with open("app/static/img/favicon.png", "rb") as f:
        logo_data = f.read()
        msg.attach(
            filename="favicon.png",
            content_type="image/png",
            data=logo_data,
            disposition="inline",
            headers=[("Content-ID", "<logo_fronesis>")]
        )

    mail.send(msg)
