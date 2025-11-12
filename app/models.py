from app import db
from datetime import datetime


class Cita(db.Model):
    __tablename__ = 'citas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo_electronico = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(50), default="pendiente")
    recordatorio_enviado = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f"<Cita {self.nombre} {self.apellido} - {self.fecha} {self.hora}>"



class DiaRestringido(db.Model):
    __tablename__ = 'dias_restringidos'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)  # opcional
    creado_en = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<DiaRestringido {self.fecha}>"



class HoraRestringida(db.Model):
    __tablename__ = 'horas_restringidas'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.now)

    # Relación opcional con DiaRestringido (no obligatoria)
    dia_id = db.Column(db.Integer, db.ForeignKey('dias_restringidos.id'), nullable=True)
    dia = db.relationship('DiaRestringido', backref=db.backref('horas_restringidas', lazy=True))

    def __repr__(self):
        return f"<HoraRestringida {self.fecha} {self.hora}>"
