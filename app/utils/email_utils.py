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

# --- Formatear fecha ---
def formatear_fecha(fecha_dt):
    dia = fecha_dt.day
    mes = MESES_ES.get(fecha_dt.month, fecha_dt.month)
    año = fecha_dt.year
    return f"{dia} de {mes} de {año}"

# --- Formatear hora 12h ---
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

        return f"{hora_12}:{minuto:02d} {sufijo}", formatear_fecha(dt).capitalize()
    except Exception as e:
        print("⚠️ Error al formatear hora:", e)
        return hora, fecha

# --- Enviar correo con Resend ---
def enviar_por_resend(destinatario, asunto, html_body):
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    if not RESEND_API_KEY:
        print("❌ ERROR: Falta variable RESEND_API_KEY en Render.")
        return

    url = "https://api.resend.com/emails"

    payload = {
        "from": "Fronesis Studio <info@fronesisstudio.fun>",
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

# --- Enviar correo principal ---
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
                "descripcion": (
                    "Lamentamos informarte que tu cita ha sido cancelada, "
                    "ya que al barbero se le presentó un imprevisto."
                ),
                "gradiente": "linear-gradient(90deg,#ff8c00,#ff4b2b,#c0392b)"
            },
            'recordatorio': {
                "asunto": "⏰ Recordatorio de tu cita - Fronesis Studio",
                "titulo": "Recordatorio de tu cita",
                "descripcion": "Tu cita se aproxima. Te esperamos en dos horas.",
                "gradiente": "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
            }
        }

        conf = tipos.get(tipo, tipos['nueva'])
        asunto, titulo, descripcion, gradiente = conf["asunto"], conf["titulo"], conf["descripcion"], conf["gradiente"]

        base_url = "https://fronesisstudio.onrender.com"

        # --- BOTONES OPTIMIZADOS PARA IPHONE Y OUTLOOK ---
        enlaces_html = ""
        if tipo not in ["cancelada", "cancelada_admin"]:
            token = encriptar_id(id_cita)
            enlaces_html = f"""
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.2);margin:25px 0;">

            <div style="margin-top:20px; text-align:center; display:flex; gap:12px;">

              <!-- BOTÓN REAGENDAR -->
              <a href="{base_url}/cliente/reagendar/{token}"
                 style="flex:1;background:{gradiente};padding:1px;border-radius:8px;
                        display:inline-block;text-decoration:none !important;">

                <div style="background:#000;border-radius:8px;padding:12px 0;">
                  <span style="color:#fff !important;font-weight:700;font-size:14px;display:block;">
                    🔁 Reagendar
                  </span>
                </div>
              </a>

              <!-- BOTÓN CANCELAR -->
              <a href="{base_url}/cliente/cancelar_cita/{token}"
                 style="flex:1;background:linear-gradient(90deg,#ff4b2b,#c0392b,#ff6b6b);
                        padding:1px;border-radius:8px;display:inline-block;
                        text-decoration:none !important;">

                <div style="background:#000;border-radius:8px;padding:12px 0;">
                  <span style="color:#fff !important;font-weight:700;font-size:14px;display:block;">
                    🚫 Cancelar
                  </span>
                </div>
              </a>

            </div>
            """

        # --- HTML FINAL ---
        html_body = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{asunto}</title>
</head>

<body style="margin:0;padding:0;font-family:Poppins,Arial,sans-serif;background:#0f0f0f;color:#fff;text-align:center;">

  <div style="margin:40px auto;max-width:420px;background:rgba(255,255,255,0.05);
       padding:30px 22px;border-radius:18px;box-shadow:0 4px 25px rgba(0,0,0,0.5);">

    <img src="https://fronesisstudio.fun/static/img/favicon.png"
         width="100" height="100"
         style="border-radius:50%;margin-bottom:20px;">

    <h2 style="font-size:22px;font-weight:600;margin-bottom:10px;
        background:{gradiente};
        -webkit-background-clip:text;background-clip:text;
        -webkit-text-fill-color:transparent;">
        {titulo}, {nombre}
    </h2>

    <p style="font-size:14px;margin-bottom:25px;">{descripcion}</p>

    <div style="border:1px solid rgba(255,255,255,0.1);padding:20px;border-radius:14px;text-align:left;">
      <h3 style="text-align:center;font-size:17px;">
        Reserva Estudio<br>
        <span style="font-weight:800;font-size:19px;">FRONESIS</span>
      </h3>

      <p>👤 {nombre}</p>
      <p>⏱ {hora}</p>
      <p>📅 {fecha}</p>
      <p>📍 Carrera 98A #131-05 — Aures</p>

      {enlaces_html}
    </div>

  </div>

</body>
</html>
"""

        print("📨 Enviando correo mediante Resend...")
        enviar_por_resend(destinatario, asunto, html_body)

    except Exception as e:
        print("❌ ERROR durante el envío del correo:", e)
        traceback.print_exc()
