# dependencias de flask
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils.scheduler_utils import marcar_citas_como_completadas, enviar_recordatorios_citas
from .config import Config

# 🔹 Crear los objetos (sin asociarlos aún)
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()


# 🔹 Función de fábrica de la app
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ Configuración de correo (deberías usar variables de entorno aquí)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'fronesisstudio2@gmail.com'
    app.config['MAIL_PASSWORD'] = 'vqab kmok uhow duxl'
    app.config['MAIL_DEFAULT_SENDER'] = ('Fronesis Studio', 'fronesisstudio2@gmail.com')

    # 🔹 Inicializar extensiones
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # ✅ Registrar blueprints después de inicializar extensiones
    from app.administrador import admin_blueprint
    from app.cliente import cliente_blueprint
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(cliente_blueprint)

    # ✅ Importar dentro del contexto para evitar errores circulares
    from .models import Cita
    from app.utils.email_utils import enviar_correo_con_invitacion  

    # 🔹 Configurar scheduler (ejecutar tareas periódicas)
    scheduler = BackgroundScheduler(daemon=True)

    # ✅ Usar lambda con contexto de aplicación
    scheduler.add_job(
        func=lambda: marcar_citas_como_completadas(app, db, Cita),
        trigger="interval",
        minutes=1
    )
    scheduler.add_job(
        enviar_recordatorios_citas,
        'interval',
        minutes=3,
        args=[app, db, Cita, enviar_correo_con_invitacion]
    )

    scheduler.start()

    # ✅ Ruta principal
    @app.route('/')
    def index():
        return render_template('cliente/calendario.html')

    return app
