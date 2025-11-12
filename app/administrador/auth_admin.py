from functools import wraps
from flask import session, redirect, url_for, request, flash

def requiere_contraseña(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        # Verifica si el usuario ya inició sesión
        if not session.get('admin_autenticado'):
            flash("🔒 Debes ingresar la contraseña de administrador.", "warning")
            # Guarda la URL actual para redirigir después del login
            return redirect(url_for('administrador.login_admin', next=request.url))
        return f(*args, **kwargs)
    return decorador
