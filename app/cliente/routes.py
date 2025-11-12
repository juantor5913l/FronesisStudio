import app
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from datetime import datetime, timedelta
import locale

from app.models import HoraRestringida
from . import cliente_blueprint
from app.config import Config
from app.utils.email_utils import enviar_correo_con_invitacion
from app.utils.security_utils import encriptar_id, desencriptar_id  # 🔒 Nuevo import

# 🔹 Configurar idioma español
locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

# -----------------------------------------------------------
# 🔹 CALENDARIO PRINCIPAL
# -----------------------------------------------------------
@cliente_blueprint.route('/calendario')
def calendario_view():
    return render_template('cliente/calendario.html')


# -----------------------------------------------------------
# 🔹 DÍAS RESTRINGIDOS (opcional)
# -----------------------------------------------------------
@cliente_blueprint.route('/dias_restringidos')
def dias_restringidos():
    from app import db, models
    dias = models.DiaRestringido.query.all()
    fechas = [d.fecha.strftime('%Y-%m-%d') for d in dias]
    return jsonify(fechas)


# -----------------------------------------------------------
# 🔹 SELECCIONAR FECHA DE NUEVA CITA
# -----------------------------------------------------------
@cliente_blueprint.route('/seleccionar_fecha', methods=['POST'])
def seleccionar_fecha():
    fecha_str = request.form.get('fecha')

    if not fecha_str:
        flash('Debe seleccionar una fecha válida.', 'warning')
        return redirect(url_for('cliente.calendario_view'))

    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    hoy = datetime.now().date()
    limite = hoy + timedelta(days=30)

    if fecha < hoy:
        flash('🚫 No puedes agendar citas en días pasados.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    if fecha > limite:
        flash('🚫 Solo puedes agendar citas hasta con un mes de anticipación.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    session['fecha_cita'] = fecha_str
    return redirect(url_for('cliente.seleccionar_hora'))


# -----------------------------------------------------------
# 🔹 HORAS DISPONIBLES
# -----------------------------------------------------------
@cliente_blueprint.route('/horas_disponibles')
def horas_disponibles():
    from app import db, models
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify([])

    citas = db.session.query(models.Cita).filter_by(fecha=fecha).all()
    ocupadas = [c.hora.strftime('%H:%M') for c in citas]

    todas = [
        '07:00', '07:45', '08:30', '09:45', '10:30', '11:15',
        '12:45', '13:30', '14:15', '15:45', '16:30', '17:15',
        '18:00', '18:45'
    ]
    libres = [h for h in todas if h not in ocupadas]
    return jsonify(libres)


# -----------------------------------------------------------
# 🔹 SELECCIONAR HORA
# -----------------------------------------------------------
@cliente_blueprint.route('/horas', methods=['GET', 'POST'])
def seleccionar_hora():
    from app import db, models
    from datetime import datetime
    from app.models import HoraRestringida

    if request.method == 'POST':
        hora = request.form.get('hora')
        if not hora:
            flash('Debe seleccionar una hora.')
            return redirect(url_for('cliente.seleccionar_hora'))

        fecha_str = session.get('fecha_cita')
        if not fecha_str:
            return redirect(url_for('cliente.calendario_view'))

        fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        hora_cita = datetime.strptime(hora, "%H:%M").time()
        ahora = datetime.now()

        if fecha_cita == ahora.date() and hora_cita <= ahora.time():
            flash('No puedes agendar una hora que ya ha pasado.')
            return redirect(url_for('cliente.seleccionar_hora'))

        session['hora_cita'] = hora
        return redirect(url_for('cliente.datos_cita'))

    fecha_str = session.get('fecha_cita')
    if not fecha_str:
        return redirect(url_for('cliente.calendario_view'))

    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    citas_existentes = db.session.query(models.Cita).filter_by(fecha=fecha).all()
    horas_ocupadas = [c.hora.strftime('%H:%M') for c in citas_existentes]

    bloqueos = db.session.query(HoraRestringida.hora).filter(
        HoraRestringida.fecha == fecha
    ).all()
    horas_bloqueadas = [h.hora.strftime('%H:%M') for h in bloqueos]

    todas_las_horas = [
        '07:00', '07:45', '08:30', '09:45', '10:30', '11:15',
        '12:45', '13:30', '14:15', '15:45', '16:30', '17:15',
        '18:00', '18:45'
    ]

    horas_disponibles = [
        h for h in todas_las_horas
        if h not in horas_ocupadas and h not in horas_bloqueadas
    ]

    ahora = datetime.now()
    if fecha == ahora.date():
        horas_disponibles = [
            h for h in horas_disponibles
            if datetime.strptime(h, "%H:%M").time() > ahora.time()
        ]

    fecha_formateada = fecha.strftime("%#d de %B de %Y")
    nombre_dia = fecha.strftime("%A")

    return render_template(
        'cliente/horas.html',
        fecha=fecha_formateada,
        horas_disponibles=horas_disponibles,
        nombre_dia=nombre_dia
    )


# -----------------------------------------------------------
# 🔹 DATOS DE CITA
# -----------------------------------------------------------
@cliente_blueprint.route('/datos', methods=['GET', 'POST'])
def datos_cita():
    from datetime import datetime
    from app import db, models

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        correo_electronico = request.form.get('correo_electronico')
        telefono = request.form.get('telefono')
        fecha = session.get('fecha_cita')
        hora = session.get('hora_cita')
        horaAm = session.get('hora_cita')

        if not telefono or not telefono.isdigit() or len(telefono) != 10:
            return "Error: el teléfono debe tener 10 dígitos."
        if not correo_electronico or '@' not in correo_electronico or '.' not in correo_electronico:
            return "Error: el correo electrónico no es válido."
        if not fecha or not hora:
            return "Error: falta la fecha u hora de la cita."

        try:
            hora_completa = f"{hora}:00" if len(hora) == 5 else hora
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
            hora_obj = datetime.strptime(hora_completa, "%H:%M:%S").time()
        except ValueError as e:
            return "Error: formato de fecha u hora inválido."

        cita_existente = models.Cita.query.filter_by(fecha=fecha, hora=hora_completa).first()
        if cita_existente:
            return "Error: Ya existe una cita agendada para ese día y hora."

        cita_pendiente = models.Cita.query.filter_by(
            correo_electronico=correo_electronico,
            estado='activa'
        ).first()
        if cita_pendiente:
            flash('⚠️ Ya tienes una cita pendiente.', 'warning')
            return redirect(url_for('cliente.calendario_view', error='pendiente'))

        nueva_cita = models.Cita(
            nombre=nombre,
            apellido=apellido,
            correo_electronico=correo_electronico,
            telefono=telefono,
            fecha=fecha,
            hora=hora_completa,
            estado='activa'
        )
        db.session.add(nueva_cita)
        db.session.commit()
        id_cita = nueva_cita.id

        enviar_correo_con_invitacion(
            id_cita=id_cita,
            destinatario=correo_electronico,
            nombre=nombre,
            fecha=fecha,
            hora=hora_completa,
            tipo='nueva'
        )

        fecha_formateada = fecha_obj.strftime("%#d de %B de %Y")

        session.pop('fecha_cita', None)
        session.pop('hora_cita', None)

        if horaAm:
            try:
                hora_obj = datetime.strptime(horaAm, "%H:%M").time()
                h = hora_obj.hour
                m = hora_obj.minute
                sufijo = "AM" if h < 12 else "PM"
                h12 = h % 12 or 12
                hora_am_pm = f"{h12}:{m:02d} {sufijo}"
            except Exception:
                hora_am_pm = horaAm
        else:
            hora_am_pm = None

        return render_template(
            'cliente/confirmacion.html',
            nombre=nombre,
            fecha_formateada=fecha_formateada,
            hora=hora,
            hora_am_pm=hora_am_pm
        )

    hora = session.get('hora_cita')
    fecha_str = session.get('fecha_cita')

    if hora:
        try:
            hora_obj = datetime.strptime(hora, "%H:%M").time()
            h = hora_obj.hour
            m = hora_obj.minute
            sufijo = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            hora_am_pm = f"{h12}:{m:02d} {sufijo}"
        except Exception:
            hora_am_pm = hora
    else:
        hora_am_pm = None

    if fecha_str:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        fecha_formateada = fecha.strftime("%#d de %B de %Y")
        nombre_dia = fecha.strftime("%A")
    else:
        fecha_formateada = ""
        nombre_dia = ""

    return render_template(
        'cliente/datos.html',
        hora=hora,
        hora_am_pm=hora_am_pm,
        fecha_formateada=fecha_formateada,
        nombre_dia=nombre_dia
    )


# -----------------------------------------------------------
# 🔹 REAGENDAR CITA (PASO 1: Seleccionar nueva fecha)
# -----------------------------------------------------------
@cliente_blueprint.route('/reagendar/<token>', methods=['GET', 'POST'])
def reagendar_fecha(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))
    cita = db.session.query(models.Cita).get_or_404(cita_id)

    if cita.hora:
        try:
            hora = cita.hora.hour
            minuto = cita.hora.minute
            sufijo = "AM" if hora < 12 else "PM"
            hora_12 = hora % 12 or 12
            cita.hora_am_pm = f"{hora_12}:{minuto:02d} {sufijo}"
        except Exception:
            cita.hora_am_pm = str(cita.hora)
    else:
        cita.hora_am_pm = None

    if request.method == 'POST':
        nueva_fecha_str = request.form.get('fecha')
        if not nueva_fecha_str:
            flash('Debe seleccionar una fecha válida.', 'warning')
            return redirect(url_for('cliente.reagendar_fecha', token=token))

        nueva_fecha = datetime.strptime(nueva_fecha_str, '%Y-%m-%d').date()
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=30)

        if nueva_fecha < hoy:
            flash('🚫 No puedes reagendar a una fecha pasada.', 'danger')
            return redirect(url_for('cliente.reagendar_fecha', token=token))
        if nueva_fecha > limite:
            flash('🚫 Solo puedes reagendar hasta dentro de un mes.', 'danger')
            return redirect(url_for('cliente.reagendar_fecha', token=token))

        session['nueva_fecha'] = nueva_fecha_str
        return redirect(url_for('cliente.reagendar_hora', token=token))

    return render_template('cliente/reagendar_fecha.html', cita=cita,token=token)


# -----------------------------------------------------------
# 🔹 REAGENDAR CITA (PASO 2: Seleccionar nueva hora)
# -----------------------------------------------------------
@cliente_blueprint.route('/reagendar/<token>/hora', methods=['GET', 'POST'])
def reagendar_hora(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))
    cita = db.session.query(models.Cita).get_or_404(cita_id)

    fecha = session.get('nueva_fecha')
    if not fecha:
        return redirect(url_for('cliente.reagendar_fecha', token=token))

    if request.method == 'POST':
        nueva_hora = request.form.get('hora')
        if not nueva_hora:
            flash('Debe seleccionar una hora válida.', 'warning')
            return redirect(url_for('cliente.reagendar_hora', token=token))

        cita_existente = db.session.query(models.Cita).filter_by(fecha=fecha, hora=nueva_hora).first()
        if cita_existente and cita_existente.id != cita.id:
            flash('🚫 Esa hora ya está ocupada.', 'danger')
            return redirect(url_for('cliente.reagendar_hora', token=token))

        session['nueva_hora'] = nueva_hora
        return redirect(url_for('cliente.reagendar_confirmar', token=token))

    citas_existentes = db.session.query(models.Cita).filter_by(fecha=fecha).all()
    horas_ocupadas = [c.hora.strftime('%H:%M') for c in citas_existentes]

    bloqueos = db.session.query(HoraRestringida.hora).filter(
        HoraRestringida.fecha == fecha
    ).all()
    horas_bloqueadas = [h.hora.strftime('%H:%M') for h in bloqueos]

    todas_las_horas = [
        '07:00', '07:45', '08:30', '09:45', '10:30', '11:15',
        '12:45', '13:30', '14:15', '15:45', '16:30', '17:15',
        '18:00', '18:45'
    ]

    horas_disponibles = [
        h for h in todas_las_horas
        if h not in horas_ocupadas and h not in horas_bloqueadas
    ]

    ahora = datetime.now()
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    if fecha_dt.date() == ahora.date():
        horas_disponibles = [
            h for h in horas_disponibles
            if datetime.strptime(f"{fecha} {h}", "%Y-%m-%d %H:%M") > ahora
        ]

    fecha_legible = fecha_dt.strftime("%#d de %B de %Y").capitalize()
    nombre_dia = fecha_dt.strftime("%A")
    hora_agendada_anterior = cita.hora.strftime('%H:%M')

    return render_template(
        'cliente/reagendar_hora.html',
        cita=cita,
        fecha=fecha,
        fecha_legible=fecha_legible,
        horas_disponibles=horas_disponibles,
        nombre_dia=nombre_dia,
        hora_agendada_anterior=hora_agendada_anterior,
    )


# -----------------------------------------------------------
# 🔹 REAGENDAR CITA (PASO 3: Confirmar y guardar)
# -----------------------------------------------------------
@cliente_blueprint.route('/reagendar/<token>/confirmar', methods=['GET', 'POST'])
def reagendar_confirmar(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))
    cita = db.session.query(models.Cita).get_or_404(cita_id)

    fecha = session.get('nueva_fecha')
    hora = session.get('nueva_hora')
    cita.estado = "activa"

    if not fecha or not hora:
        return redirect(url_for('cliente.reagendar_fecha', token=token))

    if request.method == 'POST':
        nueva_fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        ahora = datetime.now()

        if nueva_fecha_hora <= ahora + timedelta(hours=3):
            flash('⚠️ Solo puedes reagendar con al menos 3 horas de anticipación.', 'warning')
            return redirect(url_for('cliente.reagendar_hora', token=token))

    cita.fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    cita.hora = datetime.strptime(hora, '%H:%M').time()
    db.session.commit()

    enviar_correo_con_invitacion(
        id_cita=cita.id,
        destinatario=cita.correo_electronico,
        nombre=cita.nombre,
        fecha=str(cita.fecha),
        hora=str(cita.hora),
        tipo='reagendada'
    )

    session.pop('nueva_fecha', None)
    session.pop('nueva_hora', None)

    flash('✅ Cita reagendada exitosamente.', 'success')
    return redirect(url_for('cliente.confirmacion_reagendada', token=encriptar_id(cita.id)))


# -----------------------------------------------------------
# 🔹 CONFIRMACIÓN DE CITA REAGENDADA
# -----------------------------------------------------------
@cliente_blueprint.route('/confirmacion_reagendada/<token>')
def confirmacion_reagendada(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))
    cita = db.session.query(models.Cita).get_or_404(cita_id)

    if cita.hora:
        try:
            hora = cita.hora.hour
            minuto = cita.hora.minute
            sufijo = "AM" if hora < 12 else "PM"
            hora_12 = hora % 12 or 12
            cita.hora_am_pm = f"{hora_12}:{minuto:02d} {sufijo}"
        except Exception:
            cita.hora_am_pm = str(cita.hora)
    else:
        cita.hora_am_pm = None

    fecha_legible = cita.fecha.strftime("%#d de %B de %Y")

    return render_template(
        'cliente/confirmacion_reagendada.html',
        cita=cita,
        fecha_legible=fecha_legible
    )


# -----------------------------------------------------------
# 🔹 ELIMINA Y MUESTRA CONFIRMACIÓN
# -----------------------------------------------------------

@cliente_blueprint.route('/cancelar_cita/<token>', methods=['GET'])
def cancelar_cita(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    cita = db.session.query(models.Cita).get_or_404(cita_id)

    # ✅ Convertir la hora tipo datetime.time a formato 12h con AM/PM manual
    if cita.hora:
        try:
            hora = cita.hora.hour
            minuto = cita.hora.minute
            sufijo = "AM" if hora < 12 else "PM"
            hora_12 = hora % 12 or 12
            cita.hora_am_pm = f"{hora_12}:{minuto:02d} {sufijo}"
        except Exception:
            cita.hora_am_pm = str(cita.hora)
    else:
        cita.hora_am_pm = None

    token = encriptar_id(cita.id)
    return render_template('cliente/cancelar_cita.html', cita=cita, token=token)



@cliente_blueprint.route('/confirmacion_cancelar/<token>', methods=['POST'])
def confirmacion_cancelar(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    cita = db.session.query(models.Cita).get_or_404(cita_id)
    destinatario = cita.correo_electronico
    nombre = cita.nombre
    fecha = str(cita.fecha)
    hora = str(cita.hora)

    try:
        db.session.delete(cita)
        db.session.commit()
        enviar_correo_con_invitacion(
            id_cita=cita_id,
            destinatario=destinatario,
            nombre=nombre,
            fecha=fecha,
            hora=hora,
            tipo='cancelada'
        )
        flash('❌ La cita ha sido cancelada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'⚠️ Ocurrió un error al cancelar la cita: {str(e)}', 'danger')

    # ✅ Convertir la hora tipo datetime.time a formato 12h con AM/PM manual
    if cita.hora:
        try:
            hora = cita.hora.hour
            minuto = cita.hora.minute
            sufijo = "AM" if hora < 12 else "PM"
            hora_12 = hora % 12 or 12
            hora_am_pm = f"{hora_12}:{minuto:02d} {sufijo}"
        except Exception:
            hora_am_pm = str(cita.hora)
    else:
        hora_am_pm = None

    # Renderiza la página de confirmación
    return render_template(
        'cliente/confirmacion_cancelar.html',
        hora_am_pm=hora_am_pm,
        nombre=cita.nombre,
        hora=cita.hora,
        fecha_formateada=cita.fecha.strftime('%A, %d de %B de %Y')
    )
