from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..models import Actividad, UserAgenda, Asistencia
from ..extensions import db
from datetime import datetime

bp = Blueprint('api', __name__)

@bp.route('/asistencia/registrar', methods=['POST'])
@login_required
def registrar_asistencia():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token no proporcionado'}), 400
    actividad = Actividad.query.filter_by(qr_token=token).first()
    if not actividad:
        return jsonify({'error': 'Código QR inválido'}), 404
    inscripcion = UserAgenda.query.filter_by(user_id=current_user.id, actividad_id=actividad.id).first()
    if not inscripcion:
        return jsonify({'error': 'No estás inscrito en esta actividad'}), 403
    ahora = datetime.now()
    fecha_hora_inicio = datetime.strptime(f"{actividad.date} {actividad.start_time}", '%Y-%m-%d %H:%M')
    fecha_hora_fin = datetime.strptime(f"{actividad.date} {actividad.end_time}", '%Y-%m-%d %H:%M') if actividad.end_time else None
    if ahora < fecha_hora_inicio:
        return jsonify({'error': 'La actividad aún no ha comenzado'}), 403
    if fecha_hora_fin and ahora > fecha_hora_fin:
        return jsonify({'error': 'La actividad ya ha terminado'}), 403
    ya_asistio = Asistencia.query.filter_by(user_id=current_user.id, actividad_id=actividad.id).first()
    if ya_asistio:
        return jsonify({'error': 'Ya registraste tu asistencia a esta actividad'}), 403
    nueva_asistencia = Asistencia(user_id=current_user.id, actividad_id=actividad.id)
    db.session.add(nueva_asistencia)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Asistencia registrada correctamente'})