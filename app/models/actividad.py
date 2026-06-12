from ..extensions import db

class Actividad(db.Model):
    __tablename__ = 'actividad'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    day = db.Column(db.String(50))
    category = db.Column(db.String(100))
    date = db.Column(db.String(100))
    start_time = db.Column(db.String(50))
    end_time = db.Column(db.String(50))
    speaker = db.Column(db.String(200))
    venue = db.Column(db.String(200))
    description = db.Column(db.Text)
    image = db.Column(db.String(300))
    career = db.Column(db.String(200))
    institution = db.Column(db.String(200))
    speaker_email = db.Column(db.String(200))
    speaker_phone = db.Column(db.String(50))
    academic_degree = db.Column(db.String(100))
    specialty = db.Column(db.String(200))
    experience = db.Column(db.String(200))
    social = db.Column(db.String(300))
    bio = db.Column(db.Text)
    event_type = db.Column(db.String(20), default='jornada')
    jornada_numero = db.Column(db.Integer, nullable=True)
    qr_token = db.Column(db.String(100), unique=True, nullable=True)
    qr_generated_at = db.Column(db.DateTime, nullable=True)
    logo_institucion = db.Column(db.String(300), nullable=True)   # ← Campo para logos
    
    asistencias = db.relationship('Asistencia', back_populates='actividad', cascade='all, delete-orphan')
    agendas = db.relationship('UserAgenda', back_populates='actividad', cascade='all, delete-orphan')