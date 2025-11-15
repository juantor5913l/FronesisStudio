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

def formatear_fecha(fecha_dt):
    dia = fecha_dt.day
    mes = MESES_ES.get(fecha_dt.month, fecha_dt.month)
    año = fecha_dt.year
    return f"{dia} de {mes} de {año}"


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


def enviar_por_resend(destinatario, asunto, html_body):
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    if not RESEND_API_KEY:
        print("❌ ERROR: Falta variable RESEND_API_KEY.")
        sys.stdout.flush()
        return

    url = "https://api.resend.com/emails"

    payload = {
        "from": "info@fronesisstudio.fun",
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
                "descripcion": ("Lamentamos informarte que tu cita ha sido cancelada debido a un imprevisto. "
                                "Puedes reagendar en otro horario disponible."),
                "gradiente": "linear-gradient(90deg,#ff8c00,#ff4b2b,#c0392b)"
            },
            'recordatorio': {
                "asunto": "⏰ Recordatorio de tu cita - Fronesis Studio",
                "titulo": "Recordatorio de tu cita",
                "descripcion": "Tu cita se aproxima. Te esperamos dentro de 2 horas.",
                "gradiente": "linear-gradient(90deg,#007bff,#6f00ff,#00c2ff)"
            }
        }

        conf = tipos.get(tipo, tipos['nueva'])
        asunto, titulo, descripcion, gradiente = (
            conf["asunto"], conf["titulo"], conf["descripcion"], conf["gradiente"]
        )

        base_url = "https://fronesisstudio.onrender.com"
        enlaces_html = ""

        if tipo not in ["cancelada", "cancelada_admin"]:
            token = encriptar_id(id_cita)
            enlaces_html = f"""
            <hr style='border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0;'>
            <table width='100%' cellspacing='0' cellpadding='0' style='text-align:center;'>
              <tr>
                <td>
                  <a href='{base_url}/cliente/reagendar/{token}'
                  style='display:inline-block;width:47%;padding:10px 0;margin-right:6px;font-size:14px;font-weight:700;color:#fff;background:{gradiente};border-radius:8px;text-decoration:none;'>🔁 Reagendar</a>
                  <a href='{base_url}/cliente/cancelar_cita/{token}'
                  style='display:inline-block;width:47%;padding:10px 0;margin-left:6px;font-size:14px;font-weight:700;color:#fff;background:{gradiente};border-radius:8px;text-decoration:none;'>🚫 Cancelar</a>
                </td>
              </tr>
            </table>
            """

        # -------- PLANTILLA HTML COMPATIBLE PARA IPHONE MAIL --------
        html_body = f"""
<!DOCTYPE html>
<html lang='es'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <meta name='color-scheme' content='light'>
  <meta name='supported-color-schemes' content='light'>
  <title>{asunto}</title>
</head>

<body style='margin:0;padding:0;background:#0f0f0f;font-family:Poppins,sans-serif;color:#ffffff;text-align:center;'>

  <table role='presentation' width='100%' cellspacing='0' cellpadding='0'>
    <tr>
      <td align='center' style='padding:40px 0;'>

        <table role='presentation' width='420' cellspacing='0' cellpadding='0' style='max-width:420px;width:92%;background:rgba(255,255,255,0.05);border-radius:18px;box-shadow:0 4px 25px rgba(0,0,0,0.5);'>
          <tr><td style='padding:30px 22px;'>

            <table role='presentation' width='90' height='90' align='center'>
              <tr>
                <td style='padding:3px;border-radius:50%;background:{gradiente};'>
                  <img src='cid:logo_fronesis' width='84' height='84' style='border-radius:50%;display:block;'>
                </td>
              </tr>
            </table>

            <h2 style='font-size:22px;font-weight:600;margin:10px 0;background:{gradiente};-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
              {titulo}, {nombre}
            </h2>

            <p style='font-size:14px;margin:0 0 25px 0;color:#ffffff;'>{descripcion}</p>

            <table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='border:1px solid rgba(255,255,255,0.1);border-radius:14px;'>
              <tr>
                <td style='padding:20px;text-align:left;color:#ffffff;'>

                  <h3 style='text-align:center;font-size:17px;margin:0 0 14px 0;background:{gradiente};-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                    Reserva Estudio<br>
                    <span style='font-weight:800;font-size:19px;'>FRONESIS</span>
                  </h3>

                  <p style='font-size:14px;margin:10px 0;'>👤 {nombre}</p>
                  <p style='font-size:14px;margin:10px 0;'>⏱ {hora}</p>
                  <p style='font-size:14px;margin:10px 0;'>📅 {fecha}</p>
                  <p style='font-size:14px;margin:10px 0;'>📍 Carerra 98A #131-05 Aures</p>

                  {enlaces_html}

                </td>
              </tr>
            </table>

          </td></tr>
        </table>

      </td>
    </tr>
  </table>

</body>
</html>
        """

        enviar_por_resend(destinatario, asunto, html_body)

    except Exception as e:
        print("❌ ERROR durante el envío del correo:", e)
        traceback.print_exc()
        sys.stdout.flush()