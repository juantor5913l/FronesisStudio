from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
def marcar_citas_como_completadas(app, db, Cita):
    """Marca automáticamente como completadas las citas cuya fecha y hora ya pasaron."""
    with app.app_context():
        try:
            ahora = datetime.now(ZoneInfo("America/Bogota"))

            hoy = ahora.date()


            # 🔹 Citas anteriores a hoy
            citas_pasadas = Cita.query.filter(
                Cita.fecha < hoy,
                Cita.estado.in_(["activa", "confirmada"])
            ).all()

            # 🔹 Citas de hoy pero cuya hora ya pasó
            citas_de_hoy_pasadas = Cita.query.filter(
                Cita.fecha == hoy,
                Cita.hora < ahora.time(),
                Cita.estado.in_(["activa", "confirmada"])
            ).all()

            total = 0
            for cita in citas_pasadas + citas_de_hoy_pasadas:
                cita.estado = "completada"  # 🔹 se marca como completada
                total += 1

            if total > 0:
                db.session.commit()
                print(f"✅ {total} citas marcadas automáticamente como completadas.")
            else:
                print("ℹ️ No hay citas para completar en este momento.")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error al marcar citas completadas: {e}")


def enviar_recordatorios_citas(app, db, Cita, enviar_correo_con_invitacion):
    with app.app_context():
        try:

            ahora = datetime.now(ZoneInfo("America/Bogota"))

            limite_inferior = ahora + timedelta(hours=1, minutes=55)
            limite_superior = ahora + timedelta(hours=2, minutes=5)


            print("🔍 Hora actual:", ahora)
            print("🔍 Rango de búsqueda:", limite_inferior, "→", limite_superior)

            # 🔹 Buscar citas activas o confirmadas
            citas = Cita.query.filter(
                Cita.estado.in_(["activa", "confirmada"])
            ).all()

            total = 0
            for cita in citas:
                
                cita_datetime = datetime.combine(cita.fecha, cita.hora, tzinfo=ZoneInfo("America/Bogota"))


                print(f"⏰ Cita {cita.id}: {cita.fecha} {cita.hora} | recordatorio_enviado={cita.recordatorio_enviado}")

                # 🔹 Verificar que esté dentro del rango y no se haya enviado
                if (not cita.recordatorio_enviado) and (limite_inferior <= cita_datetime <= limite_superior):
                    total += 1
                    print(f"📧 Enviando recordatorio para cita {cita.id} - {cita.nombre} ({cita.fecha} {cita.hora})")

                    enviar_correo_con_invitacion(
                        destinatario=cita.correo_electronico,
                        nombre=cita.nombre,
                        fecha=str(cita.fecha),
                        hora=str(cita.hora),
                        tipo="recordatorio",
                        id_cita=cita.id
                    )

                    # 🔹 Marcar como enviado para no repetir
                    cita.recordatorio_enviado = True
                    db.session.commit()

            if total > 0:
                print(f"✅ {total} recordatorio(s) enviados correctamente.")
            else:
                print("ℹ️ No hay citas próximas en el rango establecido.")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error al enviar recordatorios: {e}")

