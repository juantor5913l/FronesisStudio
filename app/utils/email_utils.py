from datetime import datetime

def formatear_hora_12h(fecha, hora):
    """
    Convierte fecha y hora a formato legible en español (12h con AM/PM).
    Ejemplo:
      Entrada: ('2025-11-13', '14:30')
      Salida: ('2:30 p. m.', '13 de noviembre de 2025')
    """
    try:
        # Parseo de fecha y hora
        dt_fecha = datetime.strptime(fecha, "%Y-%m-%d")
        dt_hora = datetime.strptime(hora, "%H:%M")

        fecha_legible = dt_fecha.strftime("%d de %B de %Y")
        hora_legible = dt_hora.strftime("%I:%M %p").lstrip("0").replace("AM", "a. m.").replace("PM", "p. m.")
        return hora_legible, fecha_legible
    except Exception as e:
        print("⚠️ Error al formatear hora:", e)
        return hora, fecha


def enviar_correo_con_invitacion(destinatario, nombre, fecha, hora, tipo, id_cita):
    from app import mail  # Importación local evita problemas circulares
    from flask import current_app
    import os, sys, traceback
    from app.utils.security_utils import encriptar_id
    from flask_mail import Message
    try:
        # --- FORMATEO DE FECHA Y HORA ---
        if fecha.count('-') == 2 and ':' in hora:
            hora, fecha = formatear_hora_12h(fecha, hora)

        # --- CONFIGURACIÓN SEGÚN TIPO DE CITA ---
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

        # --- BLOQUE DE ENLACES ---
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

        # --- CUERPO HTML DEL CORREO ---
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

        # --- CREAR MENSAJE ---
        msg = Message(
            subject=asunto,
            sender=("Fronesis Studio", "tu_correo@gmail.com"),
            recipients=[destinatario],
            html=html_body
        )

        # --- INCRUSTAR LOGO INLINE (opcional) ---
        try:
            logo_path = os.path.join(current_app.root_path, "static", "img", "favicon.png")
            with open(logo_path, "rb") as f:
                logo_data = f.read()
                msg.attach(
                    filename="favicon.png",
                    content_type="image/png",
                    data=logo_data,
                    disposition="inline",
                    headers=[("Content-ID", "<logo_fronesis>")]
                )
        except Exception as e:
            print(f"⚠️ No se pudo adjuntar el logo: {e}")
            sys.stdout.flush()

        # --- ENVIAR CORREO ---
        print("📨 Enviando correo...")
        sys.stdout.flush()
        mail.send(msg)
        print("✅ Correo enviado correctamente.")
        sys.stdout.flush()

    except Exception as e:
        print("❌ ERROR durante el envío del correo:", e)
        traceback.print_exc()
        sys.stdout.flush()
