from flask import Blueprint, render_template, jsonify, request, Response, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from ..models import UserAgenda, Actividad
from ..extensions import db
from ..services.pdf_service import generar_pdf_actividades, send_pdf, get_all_unique_logos
from reportlab.lib.units import cm

bp = Blueprint('agenda', __name__)

@bp.route('/mi_agenda')
@login_required
def mi_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        flash("Esta sección es solo para estudiantes.", "warning")
        return redirect(url_for('public.ver_actividades'))
    return render_template('mi_agenda.html')

@bp.route('/api/agenda', methods=['GET'])
@login_required
def api_get_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        return jsonify({'error': 'No autorizado'}), 403
    agenda_ids = [ua.actividad_id for ua in UserAgenda.query.filter_by(user_id=current_user.id).all()]
    return jsonify({'saved_ids': agenda_ids})

@bp.route('/api/agenda/toggle', methods=['POST'])
@login_required
def api_toggle_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    actividad_id = data.get('actividad_id')
    if not actividad_id:
        return jsonify({'error': 'Falta actividad_id'}), 400
    actividad = Actividad.query.get(actividad_id)
    if not actividad:
        return jsonify({'error': 'Actividad no existe'}), 404

    existe = UserAgenda.query.filter_by(user_id=current_user.id, actividad_id=actividad_id).first()
    if existe:
        db.session.delete(existe)
        db.session.commit()
        return jsonify({'saved': False, 'message': 'Eliminado de tu agenda'})
    else:
        nueva = UserAgenda(user_id=current_user.id, actividad_id=actividad_id)
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'saved': True, 'message': 'Agregado a tu agenda'})

@bp.route('/mi_agenda/exportar_pdf')
@login_required
def exportar_mi_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        flash("Acceso solo para estudiantes", "warning")
        return redirect(url_for('agenda.mi_agenda'))

    agenda_items = UserAgenda.query.filter_by(user_id=current_user.id).all()
    actividades = [item.actividad for item in agenda_items]

    if not actividades:
        flash("Tu agenda está vacía. No hay nada para exportar.", "info")
        return redirect(url_for('agenda.mi_agenda'))

    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'date', 'label': 'Fecha', 'width': 2.5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm}
    ]

    # Obtener todos los logos únicos del sistema
    logos = get_all_unique_logos(current_app)

    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal="Mi Agenda Personal",
        subtitulo=f"Estudiante: {current_user.username} ({current_user.student_id or current_user.email})",
        columnas=columnas,
        mostrar_tipo_jornada=True,
        logos_unicos=logos
    )
    return send_pdf(pdf_buffer, f'Mi_Agenda_{current_user.id}.pdf')