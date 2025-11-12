# dependencias de flask
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.scheduler_utils import marcar_citas_como_completadas, enviar_recordatorios_citas
# dependencias de configuración
from .config import Config

# 🔹 Crear los objetos (sin asociarlos aún)
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()

# 🔹 Función de fábrica de la app
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from app.administrador import admin_blueprint
    from app.cliente import cliente_blueprint
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(cliente_blueprint)

    from .models import Cita
    from app.utils.email_utils import enviar_correo_con_invitacion  
    # 🔹 Configurar scheduler
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        func=lambda: marcar_citas_como_completadas(app, db, Cita),
        trigger="interval",
        minutes=1
)
    scheduler.add_job(enviar_recordatorios_citas, 'interval', minutes=3, args=[app, db, Cita, enviar_correo_con_invitacion])

    scheduler.start()

    @app.route('/')
    def index():
        return render_template('cliente/calendario.html')

    return app