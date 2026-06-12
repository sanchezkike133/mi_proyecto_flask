from ..extensions import db
from datetime import datetime

class UserAgenda(db.Model):
    __tablename__ = 'user_agenda'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=False)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='agenda')
    actividad = db.relationship('Actividad', back_populates='agendas')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'actividad_id', name='unique_user_actividad'),
    )