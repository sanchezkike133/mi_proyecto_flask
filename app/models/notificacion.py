from ..extensions import db
from datetime import datetime

class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(50), default='info')
    leida = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    usuario = db.relationship('User', back_populates='notificaciones')