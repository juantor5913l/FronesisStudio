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
    try:
        tz = pytz.timezone("America/Bogota")
        if len(hora.split(":")) == 2:
            hora = f"{hora}:00"
        dt = tz.localize(datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S"))
        hora_24 = dt.hour
        minuto = dt.minute
        sufijo = "AM" if hora_24 < 12 else "PM"
        hora_12 = hora_24 % 12 or 12
        hora_formateada = f"{hora_12}:{minuto:02d} {sufijo}"
        fecha_formateada = formatear_fecha(dt).capitalize()
        return hora_formateada, fecha_formateada
    except Exception as e:
        print("⚠️ Error al formatear hora:", e)
        return hora, fecha

# --- Función para enviar correo vía Resend ---
def enviar_por_resend(destinatario, asunto, html_body):
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    if not RESEND_API_KEY:
        print("❌ ERROR: Falta variable RESEND_API_KEY en Render.")
        sys.stdout.flush()
        return
    url = "https://api.resend.com/emails"
    
    payload = {
        "from": "info@fronesisstudio.fun",   # tu correo profesional
        "to": [destinatario],
        "subject": asunto,
        "html": html_body
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        print("📨 Resend status:", r.status_code)
        if r.status_code >= 400:
            print("❌ Error al enviar correo:", r.text)
        else:
            print("✅ Correo enviado correctamente.")
    except requests.exceptions.RequestException as e:
        print("❌ ERROR de conexión con Resend:", e)

# --- Función principal ---
def enviar_correo_con_invitacion(destinatario, nombre, fecha, hora, tipo, id_cita):
    try:
        if fecha and hora:
            hora, fecha = formatear_hora_12h(fecha, hora)

        tipos = {
            'nueva': {
                "asunto": "✅ Confirmación de tu cita en Fronesis Studio",
                "titulo": "Confirmación de tu cita",
                "descripcion": "Tu cita ha sido agendada exitosamente.",
                "gradiente": "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
            },
            'reagendada': {
                "asunto": "🔄 Tu cita ha sido reagendada",
                "titulo": "Tu cita ha sido reagendada",
                "descripcion": "Tu cita ha sido actualizada con nueva fecha y hora.",
                "gradiente": "linear-gradient(90deg,#e67e22,#ff9900,#ffd580)"
            },
            'cancelada': {
                "asunto": "❌ Tu cita ha sido cancelada",
                "titulo": "Tu cita ha sido cancelada",
                "descripcion": "Tu cita fue cancelada correctamente.",
                "gradiente": "linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b)"
            },
            'cancelada_admin': {
                "asunto": "⚠️ Tu cita ha sido cancelada por el barbero",
                "titulo": "Cancelación por parte del estudio",
                "descripcion": ("Lamentamos informarte que tu cita ha sido cancelada, "
                                "ya que al barbero se le presentó un imprevisto para ese día. "
                                "Puedes reagendar en otro horario disponible."),
                "gradiente": "linear-gradient(90deg,#ff8c00,#ff4b2b,#c0392b)"
            },
            'recordatorio': {
                "asunto": "⏰ Recordatorio de tu cita - Fronesis Studio",
                "titulo": "Recordatorio de tu cita",
                "descripcion": "Tu cita se aproxima. Te esperamos en Frónesis Studio dentro de 2 horas.",
                "gradiente": "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
            }
        }

        conf = tipos.get(tipo, tipos['nueva'])
        asunto, titulo, descripcion, gradiente = conf["asunto"], conf["titulo"], conf["descripcion"], conf["gradiente"]

        base_url = "https://fronesisstudio.onrender.com"
        enlaces_html = ""
        if tipo not in ["cancelada", "cancelada_admin"]:
            token = encriptar_id(id_cita)
            enlaces_html = f"""
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0;">
            <div style="display:flex;justify-content:center;align-items:center;margin-top:20px;">
              <a href='{base_url}/cliente/reagendar/{token}'
                 style="display:inline-block;width:47%;margin-right:6px;padding:1px 1px;font-size:14px;font-weight:700;text-align:center;text-decoration:none;color:#fff;border-radius:8px;
                 background-color:#007bff; background-image:-webkit-linear-gradient(90deg,#007bff,#6f00ff,#00c2ff); background-image:{gradiente};">
                  <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🔁 Reagendar</span>
              </a>
              <a href='{base_url}/cliente/cancelar_cita/{token}'
                 style="display:inline-block;width:47%;margin-left:6px;padding:1px 1px;font-size:14px;font-weight:700;text-align:center;text-decoration:none;color:#fff;border-radius:8px;
                 background-color:#ff4b2b; background-image:-webkit-linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b); background-image:{gradiente};">
                  <span style='display:block;background:#000;border-radius:8px;padding:9px 0;margin:1px;'>🚫 Cancelar</span>
              </a>
            </div>
            """

        html_body = f"""
<!DOCTYPE html>
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
<body style="margin:0;padding:0;font-family:'Poppins',sans-serif;
background:linear-gradient(135deg,rgba(15,15,15,0.95),rgba(25,25,25,0.98));
color:#ffffff !important;text-align:center;">

  <div style="margin:40px auto;max-width:420px;width:92%;border-radius:18px;
  background:rgba(255,255,255,0.05);box-shadow:0 4px 25px rgba(0,0,0,0.5);
  padding:30px 22px;">

    <!-- LOGO EN CÍRCULO -->
    <table role="presentation" width="90" height="90" align="center" cellspacing="0" cellpadding="0" border="0" 
          style="border-collapse:collapse;border-radius:50%;
          background-color:#007bff; 
          background-image:-webkit-linear-gradient(90deg,{gradiente});
          background-image:{gradiente};
          margin:0 auto 20px auto;">
      <tr>
        <td align="center" valign="middle" 
            style="border-radius:50%;background:#0f0f0f;padding:3px;">
          <img src="../static/img/favicon.png" alt="Logo Fronesis" width="84" height="84" 
               style="border-radius:50%;display:block;">
        </td>
      </tr>
    </table>

    <!-- TÍTULO -->
    <h2 style="font-size:22px;font-weight:600;margin:0 0 10px 0;
    background-color:#007bff;
    background-image:-webkit-linear-gradient(90deg,{gradiente});
    background-image:{gradiente};
    -webkit-background-clip:text;background-clip:text;
    -webkit-text-fill-color:transparent;">
      {titulo}, {nombre}
    </h2>

    <p style="color:#ffffff;font-size:14px;margin:0 0 25px 0;">{descripcion}</p>

    <div style="border:1px solid rgba(255,255,255,0.1);border-radius:14px;
    padding:20px;text-align:left;color:#ffffff !important;">
      <h3 style="text-align:center;font-size:17px;margin:0 0 14px 0;
      background-color:#007bff;
      background-image:-webkit-linear-gradient(90deg,{gradiente});
      background-image:{gradiente};
      -webkit-background-clip:text;background-clip:text;
      -webkit-text-fill-color:transparent;">
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

        print("📨 Enviando correo mediante resend...")
        sys.stdout.flush()
        enviar_por_resend(destinatario, asunto, html_body)

    except Exception as e:
        print("❌ ERROR durante el envío del correo:", e)
        traceback.print_exc()
        sys.stdout.flush()
