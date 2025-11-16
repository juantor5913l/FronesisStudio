import app
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from datetime import datetime, timedelta
import pytz
from app.models import HoraRestringida
from . import cliente_blueprint
from app.config import Config
from app.utils.email_utils import enviar_correo_con_invitacion
from app.utils.security_utils import encriptar_id, desencriptar_id
from flask import current_app
from zoneinfo import ZoneInfo

# -----------------------------------------------------------
# 🔹 FUNCIONES PARA FORMATEAR FECHAS EN ESPAÑOL
# -----------------------------------------------------------
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}

DIAS_ES = {
    "Monday": "lunes",
    "Tuesday": "martes",
    "Wednesday": "miércoles",
    "Thursday": "jueves",
    "Friday": "viernes",
    "Saturday": "sábado",
    "Sunday": "domingo"
}

def formatear_fecha(fecha_dt):
    dia = fecha_dt.day
    mes = MESES_ES[fecha_dt.month]
    año = fecha_dt.year
    return f"{dia} de {mes} de {año}"

def nombre_dia_func(fecha_dt):
    return DIAS_ES[fecha_dt.strftime("%A")]

# -----------------------------------------------------------
# 🔹 CALENDARIO PRINCIPAL
# -----------------------------------------------------------
@cliente_blueprint.route('/calendario')
def calendario_view():
    return render_template('cliente/calendario.html')

# -----------------------------------------------------------
# 🔹 DÍAS RESTRINGIDOS
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
    ahora = datetime.now(ZoneInfo("America/Bogota"))
    hoy= ahora.date()
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
    from app.models import HoraRestringida
    ahora = datetime.now(ZoneInfo("America/Bogota"))
    print("Fechaaaaaaaaaaaaaaaaaaa seleccionada:", ahora)
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
        ahora = datetime.now(ZoneInfo("America/Bogota"))


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

    bloqueos = db.session.query(HoraRestringida.hora).filter(HoraRestringida.fecha == fecha).all()
    horas_bloqueadas = [h.hora.strftime('%H:%M') for h in bloqueos]

    todas_las_horas = [
        '07:00', '07:45', '08:30', '09:45', '10:30', '11:15',
        '12:45', '13:30', '14:15', '15:45', '16:30', '17:15',
        '18:00', '18:45'
    ]


    horas_disponibles = [h for h in todas_las_horas if h not in horas_ocupadas and h not in horas_bloqueadas]

    ahora = datetime.now(ZoneInfo("America/Bogota"))

    if fecha == ahora.date():
        horas_disponibles = [h for h in horas_disponibles if datetime.strptime(h, "%H:%M").time() > ahora.time()]

    fecha_formateada = formatear_fecha(fecha)
    nombre_dia_str = nombre_dia_func(fecha)

    return render_template('cliente/horas.html',
                           fecha=fecha_formateada,
                           horas_disponibles=horas_disponibles,
                           nombre_dia=nombre_dia_str)

# -----------------------------------------------------------
# 🔹 DATOS DE CITA
# -----------------------------------------------------------
@cliente_blueprint.route('/datos', methods=['GET', 'POST'])
def datos_cita():
    from app import db, models

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip().title()
        apellido = request.form.get('apellido', '').strip().title()
        correo_electronico = request.form.get('correo_electronico')
        telefono = request.form.get('telefono')
        fecha = session.get('fecha_cita')
        hora = session.get('hora_cita')

        if not telefono or not telefono.isdigit() or len(telefono) != 10:
            return redirect(url_for('cliente.calendario_view'))
        if not correo_electronico or '@' not in correo_electronico or '.' not in correo_electronico:
            return redirect(url_for('cliente.calendario_view'))
        if not fecha or not hora:
            return redirect(url_for('cliente.calendario_view'))

        try:
            hora_completa = f"{hora}:00" if len(hora) == 5 else hora
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
            hora_obj = datetime.strptime(hora_completa, "%H:%M:%S").time()
        except ValueError:
            return redirect(url_for('cliente.calendario_view'))

        cita_existente = models.Cita.query.filter_by(fecha=fecha, hora=hora_completa).first()
        if cita_existente:
            return redirect(url_for('cliente.calendario_view'))

        cita_pendiente = models.Cita.query.filter_by(correo_electronico=correo_electronico, estado='activa').first()
        if cita_pendiente:
            flash('⚠️ Ya tienes una cita pendiente.', 'warning')
            return redirect(url_for('cliente.calendario_view', error='pendiente'))

        nueva_cita = models.Cita(nombre=nombre, apellido=apellido,
                                 correo_electronico=correo_electronico, telefono=telefono,
                                 fecha=fecha, hora=hora_completa, estado='activa')
        db.session.add(nueva_cita)
        db.session.commit()
        print(f"Cita creada: {nueva_cita.id} para {nueva_cita.nombre} el {nueva_cita.fecha} a las {nueva_cita.hora}")
        enviar_correo_con_invitacion(
            destinatario=nueva_cita.correo_electronico,
            nombre=nueva_cita.nombre,
            fecha=str(nueva_cita.fecha),
            hora=str(nueva_cita.hora),
            tipo='nueva',
            id_cita=nueva_cita.id
        )
        # Después de crear la cita
        print(f"Correo de confirmación enviado a {nueva_cita.correo_electronico}.")


        fecha_formateada = formatear_fecha(fecha_obj)
        session.pop('fecha_cita', None)
        session.pop('hora_cita', None)

        h = datetime.strptime(hora, "%H:%M").hour
        m = datetime.strptime(hora, "%H:%M").minute
        sufijo = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        hora_am_pm = f"{h12}:{m:02d} {sufijo}"

        return render_template('cliente/confirmacion.html',
                               nombre=nombre,
                               fecha_formateada=fecha_formateada,
                               hora=hora,
                               hora_am_pm=hora_am_pm)

    # GET request
    hora = session.get('hora_cita')
    fecha_str = session.get('fecha_cita')

    if hora:
        h = datetime.strptime(hora, "%H:%M").hour
        m = datetime.strptime(hora, "%H:%M").minute
        sufijo = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        hora_am_pm = f"{h12}:{m:02d} {sufijo}"
    else:
        hora_am_pm = None

    if fecha_str:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        fecha_formateada = formatear_fecha(fecha)
        nombre_dia_str = nombre_dia_func(fecha)
    else:
        fecha_formateada = ""
        nombre_dia_str = ""

    return render_template('cliente/datos.html',
                           hora=hora,
                           hora_am_pm=hora_am_pm,
                           fecha_formateada=fecha_formateada,
                           nombre_dia=nombre_dia_str)


# -----------------------------------------------------------
# 🔹 REAGENDAR CITA (PASO 1: Seleccionar nueva fecha)
# -----------------------------------------------------------
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

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
        hoy = datetime.now(ZoneInfo("America/Bogota")).date()
        limite = hoy + timedelta(days=30)

        if nueva_fecha < hoy:
            flash('🚫 No puedes reagendar a una fecha pasada.', 'danger')
            return redirect(url_for('cliente.reagendar_fecha', token=token))
        if nueva_fecha > limite:
            flash('🚫 Solo puedes reagendar hasta dentro de un mes.', 'danger')
            return redirect(url_for('cliente.reagendar_fecha', token=token))

        session['nueva_fecha'] = nueva_fecha_str
        return redirect(url_for('cliente.reagendar_fecha', token=token))

    fecha_legible = formatear_fecha(cita.fecha)
    return render_template('cliente/reagendar_fecha.html', cita=cita, fecha_legible=fecha_legible, token=token)


# -----------------------------------------------------------
# 🔹 REAGENDAR CITA (PASO 2: Seleccionar nueva hora)
# -----------------------------------------------------------
@cliente_blueprint.route('/reagendar/<token>/confirmar', methods=['GET', 'POST'])
def reagendar_confirmar(token):
    from app import db, models
    cita_id = desencriptar_id(token)
    tz = ZoneInfo("America/Bogota")
    ahora = datetime.now(tz)

    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    cita = db.session.query(models.Cita).get_or_404(cita_id)
    fecha = session.get('nueva_fecha')
    hora = session.get('nueva_hora')

    # Si falta fecha u hora, volver al paso de selección
    if not fecha or not hora:
        return redirect(url_for('cliente.reagendar_fecha', token=token))

    # POST → Guardar y enviar correo
    if request.method == 'POST':

        nueva_fecha_hora = datetime.strptime(
            f"{fecha} {hora}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)

        if nueva_fecha_hora <= ahora + timedelta(hours=3):
            flash('⚠️ Solo puedes reagendar con al menos 3 horas de anticipación.', 'warning')
            return redirect(url_for('cliente.reagendar_hora', token=token))

        # GUARDAR CAMBIOS
        cita.fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        cita.hora = datetime.strptime(hora, '%H:%M').time()
        cita.estado = "activa"
        db.session.commit()

        print(f"[OK] Cita {cita.id} REAGENDADA: {cita.fecha} {cita.hora}")

        # ENVIAR CORREO
        enviar_correo_con_invitacion(
            id_cita=cita.id,
            destinatario=cita.correo_electronico,
            nombre=cita.nombre,
            fecha=fecha,
            hora=hora,
            tipo='reagendada'
        )

        # limpiar sesión
        session.pop('nueva_fecha', None)
        session.pop('nueva_hora', None)

        return redirect(url_for('cliente.confirmacion_reagendada', token=encriptar_id(cita.id)))

    # GET → mostrar vista previa
    fecha_legible = formatear_fecha(cita.fecha)
    return render_template('cliente/confirmacion_reagendada.html', cita=cita, fecha_legible=fecha_legible)

# -----------------------------------------------------------
# 🔹 CONFIRMACIÓN FINAL
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

    fecha_legible = formatear_fecha(cita.fecha)

    return render_template(
        'cliente/confirmacion_reagendada.html',
        cita=cita,
        fecha_legible=fecha_legible
    )

# -----------------------------------------------------------
# 🔹 CANCELAR CITA
# -----------------------------------------------------------
@cliente_blueprint.route('/cancelar_cita/<token>', methods=['GET'])
def cancelar_cita(token):
    from app import db, models
    cita_id = desencriptar_id(token)
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
    if not cita_id:
        flash('Token inválido o expirado.', 'danger')
        return redirect(url_for('cliente.calendario_view'))

    cita = db.session.query(models.Cita).get_or_404(cita_id)
    token = encriptar_id(cita.id)
    return render_template('cliente/cancelar_cita.html', cita=cita, token=token)

# -----------------------------------------------------------
# 🔹 CONFIRMAR CANCELACIÓN
# -----------------------------------------------------------
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
    token = encriptar_id(cita.id)
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
        

    except Exception as e:
        db.session.rollback()
        flash(f'⚠️ Ocurrió un error al cancelar la cita: {str(e)}', 'danger')

    return render_template(
        'cliente/confirmacion_cancelar.html',
        token=token,    
        nombre=nombre,
        hora=hora,
        fecha_formateada=formatear_fecha(cita.fecha)
    )
