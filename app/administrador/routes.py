from datetime import datetime
from flask import render_template, request, redirect, session, url_for, flash, jsonify
import app
from . import admin_blueprint
from .auth_admin import requiere_contraseña


# ---------------------------------------------------------
# 🔹 LISTAR CITAS
# ---------------------------------------------------------
@admin_blueprint.route('/listar_cortes', methods=['GET'])
def listar_cortes():
    from app import db, models
    lista_cortes = db.session.query(models.Cita).all()
    return render_template('administrador/listar_cortes.html', lista_cortes=lista_cortes)




@admin_blueprint.route('/dias_restringidos/hora/<fecha_str>', methods=['GET', 'POST'])
def seleccionar_hora(fecha_str):
    from app.models import DiaRestringido, HoraRestringida, Cita
    from app import db
    from app.utils.email_utils import enviar_correo_con_invitacion
    from datetime import datetime
    from flask import jsonify, request, render_template

    try:
        fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Fecha inválida."}), 400

    todas_las_horas = [
        '07:00', '07:45', '08:30', '09:45', '10:30', '11:15',
        '12:45', '13:30', '14:15', '15:45', '16:30', '17:15',
        '18:00', '18:45'
    ]

    horas_restringidas = HoraRestringida.query.filter_by(fecha=fecha_dt).all()
    horas_restringidas_str = [h.hora.strftime('%H:%M') for h in horas_restringidas]
    dia_completo = DiaRestringido.query.filter_by(fecha=fecha_dt).first() is not None

    if request.method == 'POST':
        horas_seleccionadas = request.form.getlist('horas')
        restringir_dia = request.form.get('restringir_dia') == 'on'

        try:
            if restringir_dia:
                existente = DiaRestringido.query.filter_by(fecha=fecha_dt).first()
                if not existente:
                    db.session.add(DiaRestringido(fecha=fecha_dt))
                HoraRestringida.query.filter_by(fecha=fecha_dt).delete()

                citas_afectadas = Cita.query.filter_by(fecha=fecha_dt).all()
                if citas_afectadas:
                    for cita in citas_afectadas:
                        try:
                            enviar_correo_con_invitacion(
                                destinatario=cita.correo_electronico,
                                nombre=cita.nombre,
                                fecha=str(cita.fecha),
                                hora=str(cita.hora),
                                tipo='cancelada_admin',
                                id_cita=cita.id
                            )
                        except Exception as e:
                            print(f"[ERROR] Correo no enviado a {cita.correo_electronico}: {e}")
                        db.session.delete(cita)  # ⬅️ Aquí eliminamos la cita

                    db.session.commit()
                    return jsonify({
                        "mensaje": "📧 Día restringido. Citas eliminadas y correos enviados."
                    }), 200
                else:
                    db.session.commit()
                    return jsonify({
                        "mensaje": "✅ Día restringido correctamente. No había citas agendadas."
                    }), 200

            else:
                DiaRestringido.query.filter_by(fecha=fecha_dt).delete()
                HoraRestringida.query.filter_by(fecha=fecha_dt).delete()

                horas_dt = []
                for hora_str in horas_seleccionadas:
                    hora_dt = datetime.strptime(hora_str, '%H:%M').time()
                    db.session.add(HoraRestringida(fecha=fecha_dt, hora=hora_dt))
                    horas_dt.append(hora_dt)

                citas_afectadas = []
                if horas_dt:
                    citas_afectadas = Cita.query.filter(
                        Cita.fecha == fecha_dt,
                        Cita.hora.in_(horas_dt)
                    ).all()

                if citas_afectadas:
                    for cita in citas_afectadas:
                        try:
                            enviar_correo_con_invitacion(
                                destinatario=cita.correo_electronico,
                                nombre=cita.nombre,
                                fecha=str(cita.fecha),
                                hora=str(cita.hora),
                                tipo='cancelada_admin',
                                id_cita=cita.id
                            )
                        except Exception as e:
                            print(f"[ERROR] Correo no enviado a {cita.correo_electronico}: {e}")
                        db.session.delete(cita)  # ⬅️ Eliminamos la cita

                    db.session.commit()
                    return jsonify({
                        "mensaje": "📧 Horas restringidas. Citas eliminadas y correos enviados."
                    }), 200
                else:
                    db.session.commit()
                    return jsonify({
                        "mensaje": "✅ Restricciones aplicadas correctamente. No había citas afectadas."
                    }), 200

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error al guardar restricción: {e}")
            return jsonify({
                "error": "❌ Error al guardar restricción en la base de datos."
            }), 500

    return render_template(
        'administrador/seleccionar_hora.html',
        fecha=fecha_str,
        fecha_formateada=fecha_dt.strftime("%#d de %B de %Y"),
        todas_las_horas=todas_las_horas,
        horas_restringidas=horas_restringidas_str,
        dia_completo=dia_completo
    )



# ---------------------------------------------------------
# 🔹 LISTAR DÍAS RESTRINGIDOS
# ---------------------------------------------------------
@admin_blueprint.route('/dias_restringidos', methods=['GET'])
@requiere_contraseña

def listar_dias_restringidos():
    from app.models import DiaRestringido, HoraRestringida
    dias = DiaRestringido.query.all()
    horas = HoraRestringida.query.all()

    # Agrupar horas por fecha
    horas_por_fecha = {}
    for h in horas:
        fecha_str = h.fecha.strftime('%Y-%m-%d')
        if fecha_str not in horas_por_fecha:
            horas_por_fecha[fecha_str] = []
        horas_por_fecha[fecha_str].append(h.hora.strftime('%H:%M'))

    return render_template(
        'administrador/admin_calendario.html',
        dias=dias,
        horas_por_fecha=horas_por_fecha
    )


# ---------------------------------------------------------
# 🔹 ELIMINAR DÍA RESTRINGIDO COMPLETO
# ---------------------------------------------------------
@admin_blueprint.route('/dias_restringidos/eliminar/<fecha>', methods=['POST'])
@requiere_contraseña

def eliminar_dia_restringido(fecha):
    from app.models import DiaRestringido, HoraRestringida
    from app import db

    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()

    try:
        DiaRestringido.query.filter_by(fecha=fecha_dt).delete()
        HoraRestringida.query.filter_by(fecha=fecha_dt).delete()
        db.session.commit()
        flash(f"Restricciones del {fecha} eliminadas correctamente 🗑️")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar restricciones del {fecha}: {e}")

    return redirect(url_for('administrador.citas_por_dia', fecha=fecha))


# ---------------------------------------------------------
# 🔹 EDITAR DÍA RESTRINGIDO (lleva directo al formulario)
# ---------------------------------------------------------
@admin_blueprint.route('/dias_restringidos/editar/<fecha>', methods=['GET'])
@requiere_contraseña

def editar_dia_restringido(fecha):
    """Guarda la fecha seleccionada en la sesión y redirige al formulario."""
    session['fecha_seleccionada'] = fecha
    
    return redirect(url_for('administrador.seleccionar_hora'))
@admin_blueprint.route('/calendario')
def admin_calendario_view():
    return render_template('administrador/admin_calendario.html')




# ---------------------------------------------------------
# 🔹 ENDPOINT: DÍAS RESTRINGIDOS (para FullCalendar)
# ---------------------------------------------------------
@admin_blueprint.route('/dias_restringidos/json')
@requiere_contraseña

def dias_restringidos_json():
    from app.models import DiaRestringido
    dias = DiaRestringido.query.all()
    fechas = [d.fecha.strftime('%Y-%m-%d') for d in dias]
    return jsonify(fechas)


# ---------------------------------------------------------
# 🔹 ENDPOINT: CITAS (para FullCalendar)
# ---------------------------------------------------------
@admin_blueprint.route('/citas')
@requiere_contraseña

def citas_json():
    from app.models import Cita
    citas = Cita.query.all()

    citas_data = [
        {
            "id": c.id,
            "nombre": c.nombre,
            "apellido": c.apellido,
            "correo_electronico": c.correo_electronico,
            "telefono": c.telefono,
            "fecha": c.fecha.strftime("%Y-%m-%d"),
            "hora": c.hora.strftime("%H:%M")
        }
        for c in citas
    ]

    return jsonify(citas_data)

@admin_blueprint.route('/horas_restringidas')
@requiere_contraseña

def horas_restringidas_json():
    from app import db, models
    horas = db.session.query(models.HoraRestringida).all()
    return jsonify([{"fecha": h.fecha.strftime('%Y-%m-%d')} for h in horas])

@admin_blueprint.route('/horas/<fecha>')
@requiere_contraseña

def citas_por_dia(fecha):
    import os
    import locale
    from datetime import datetime
    from app import models

    # Establecer idioma español (según el sistema operativo)
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # Linux / Mac
    except:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')  # Windows

    # Convertir la fecha string a objeto datetime
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return f"Formato de fecha inválido: {fecha}", 400

    # Consultar las citas del día
    citas = models.Cita.query.filter_by(fecha=fecha_obj).order_by(models.Cita.hora.asc()).all()

    # Formatear fecha en español
    formato = "%#d de %B de %Y" if os.name == "nt" else "%-d de %B de %Y"
    fecha_formateada = fecha_obj.strftime(formato)


    # Día de la semana
    nombre_dia = fecha_obj.strftime("%A").capitalize()

    return render_template(
        'administrador/citas_por_dia.html',
        fecha=fecha,  # versión ISO
        fecha_formateada=fecha_formateada,  # versión legible
        nombre_dia=nombre_dia,
        citas=citas
    )


@admin_blueprint.route('/restringir_dia_directo/<fecha>', methods=['POST'])
@requiere_contraseña
def restringir_dia_directo(fecha):
    from app.models import DiaRestringido
    from app import db

    try:
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()

        existente = DiaRestringido.query.filter_by(fecha=fecha_dt).first()
        if not existente:
            db.session.add(DiaRestringido(fecha=fecha_dt))
            db.session.commit()
            return jsonify({'ok': True, 'msg': 'Día restringido correctamente ✅'})
        else:
            return jsonify({'ok': False, 'msg': '⚠️ Este día ya estaba restringido.'})

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] restringir_dia_directo: {e}")
        return jsonify({'ok': False, 'msg': '❌ Error al restringir el día.'}), 500


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        password = request.form.get('password')
        # Cambia la contraseña por la que quieras
        if password == "fronesis2025":
            session['admin_autenticado'] = True
            flash("✅ Acceso concedido.", "success")
            next_url = request.args.get('next')
            return redirect(next_url or url_for('administrador.listar_cortes'))
        else:
            flash("❌ Contraseña incorrecta.", "error")

    return render_template('administrador/login_admin.html')


@admin_blueprint.route('/logout')
def logout_admin():
    session.pop('admin_autenticado', None)
    flash("🔓 Sesión cerrada.", "info")
    return redirect(url_for('administrador.login_admin'))
