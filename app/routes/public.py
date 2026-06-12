from flask import Blueprint, render_template, jsonify
from ..models import Actividad
from ..extensions import db

bp = Blueprint('public', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/ver_actividades')
def ver_actividades():
    actividades = Actividad.query.all()
    return render_template('ver_actividades.html', actividades=actividades)

@bp.route('/conferencistas')
def ver_conferencistas():
    conferencistas = db.session.query(
        Actividad.speaker,
        Actividad.speaker_email,
        Actividad.speaker_phone,
        Actividad.academic_degree,
        Actividad.specialty,
        Actividad.experience,
        Actividad.social,
        Actividad.bio,
        Actividad.image,
        Actividad.title,
        Actividad.day,
        Actividad.start_time
    ).filter(Actividad.speaker.isnot(None)).distinct().all()
    
    conferencistas_dict = {}
    for c in conferencistas:
        if c[0] not in conferencistas_dict:
            conferencistas_dict[c[0]] = {
                'nombre': c[0], 'email': c[1], 'telefono': c[2], 'grado': c[3],
                'especialidad': c[4], 'experiencia': c[5], 'social': c[6], 'bio': c[7],
                'imagen': c[8], 'actividades': []
            }
        if c[9]:
            conferencistas_dict[c[0]]['actividades'].append({
                'titulo': c[9], 'dia': c[10], 'hora': c[11]
            })
    # Convertir dict_values a lista para que sea serializable a JSON
    return render_template('conferencistas.html', conferencistas=list(conferencistas_dict.values()))

@bp.route('/detalle/<int:id>')
def detalle(id):
    actividad = Actividad.query.get_or_404(id)
    return render_template('detalle.html', actividad=actividad)

@bp.route('/api/actividades')
def api_actividades():
    actividades = Actividad.query.all()
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'day': a.day,
        'category': a.category,
        'date': a.date,
        'start_time': a.start_time,
        'end_time': a.end_time,
        'speaker': a.speaker,
        'venue': a.venue,
        'description': a.description,
        'image': a.image,
        'event_type': a.event_type,
        'jornada_numero': a.jornada_numero,
        'qr_token': a.qr_token,
        'career': a.career,
        'institution': a.institution,
        'speaker_email': a.speaker_email,
        'speaker_phone': a.speaker_phone,
        'academic_degree': a.academic_degree,
        'specialty': a.specialty,
        'experience': a.experience,
        'social': a.social,
        'bio': a.bio
    } for a in actividades])