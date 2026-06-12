from ..extensions import db
from datetime import datetime

class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=False)
    fecha_hora_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='asistencias')
    actividad = db.relationship('Actividad', back_populates='asistencias')