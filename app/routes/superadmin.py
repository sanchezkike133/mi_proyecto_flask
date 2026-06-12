from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from ..models import User, Role, Notificacion, ActivityLog
from ..models.agenda import UserAgenda
from ..models.asistencia import Asistencia
from ..models.others import VerificationCode, PasswordReset
from ..extensions import db
from ..decorators import superadmin_required
from ..utils import init_roles_and_permissions

bp = Blueprint('superadmin', __name__)

@bp.route('/api/usuarios')
@login_required
@superadmin_required
def api_listar_usuarios():
    usuarios = User.query.all()
    return jsonify([{
        'id': u.id,
        'student_id': u.student_id,
        'username': u.username,
        'email': u.email,
        'phone': u.phone or '',
        'role_name': u.role.name if u.role else 'sin_rol',
        'is_active': u.is_active
    } for u in usuarios])

@bp.route('/api/usuario/<int:id>')
@login_required
@superadmin_required
def api_obtener_usuario(id):
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone or '',
        'role_name': user.role.name if user.role else 'estudiante',
        'is_active': user.is_active
    })

@bp.route('/api/usuario/<int:id>', methods=['PUT'])
@login_required
@superadmin_required
def api_actualizar_usuario(id):
    user = User.query.get_or_404(id)
    if user.role and user.role.name == 'superadmin':
        data = request.get_json()
        if 'is_active' in data:
            return jsonify({'error': 'No se puede cambiar el estado de un superadministrador'}), 403
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data and data['role'] != 'superadmin':
            return jsonify({'error': 'No se puede cambiar el rol de un superadministrador'}), 403
        if 'new_password' in data and data['new_password'] and len(data['new_password']) >= 6:
            user.set_password(data['new_password'])
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action=f'edit_user_{id}', actividad_id=None)
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Usuario superadmin actualizado correctamente'})
    else:
        data = request.get_json()
        cambios = []
        if 'username' in data and data['username'] != user.username:
            user.username = data['username']
            cambios.append("nombre")
        if 'email' in data and data['email'] != user.email:
            user.email = data['email']
            cambios.append("email")
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            new_role = Role.query.filter_by(name=data['role']).first()
            if new_role and new_role != user.role:
                user.role = new_role
                cambios.append("rol")
        if 'new_password' in data and data['new_password'] and len(data['new_password']) >= 6:
            user.set_password(data['new_password'])
            cambios.append("contraseña")
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            cambios.append(f"estado a {'activo' if user.is_active else 'inactivo'}")
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action=f'edit_user_{id}', actividad_id=None)
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Usuario actualizado correctamente'})

@bp.route('/api/usuario/<int:id>', methods=['DELETE'])
@login_required
@superadmin_required
def api_eliminar_usuario(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 403
    if user.role and user.role.name == 'superadmin':
        return jsonify({'error': 'No puedes eliminar un superadministrador'}), 403
    nombre = user.username
    email = user.email
    try:
        UserAgenda.query.filter_by(user_id=user.id).delete()
        ActivityLog.query.filter_by(user_id=user.id).delete()
        Asistencia.query.filter_by(user_id=user.id).delete()
        Notificacion.query.filter_by(usuario_id=user.id).delete()
        VerificationCode.query.filter_by(phone=user.email).delete()
        PasswordReset.query.filter_by(email=user.email).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': f'Usuario {nombre} eliminado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar usuario: {str(e)}'}), 500

@bp.route('/api/crear_admin', methods=['POST'])
@login_required
@superadmin_required
def api_crear_admin():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password or len(password) < 6:
        return jsonify({'error': 'Datos inválidos'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado'}), 400
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        return jsonify({'error': 'Rol admin no existe'}), 500
    new_admin = User(username=username, email=email, role=admin_role, is_active=True)
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()
    log = ActivityLog(user_id=current_user.id, action=f'crear_admin_{new_admin.id}', actividad_id=None)
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': f'Administrador {username} creado correctamente'})

@bp.route('/api/notificaciones')
@login_required
@superadmin_required
def api_notificaciones():
    notificaciones = Notificacion.query.order_by(Notificacion.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': n.id,
        'mensaje': n.mensaje,
        'tipo': n.tipo,
        'leida': n.leida,
        'timestamp': n.timestamp.isoformat()
    } for n in notificaciones])

@bp.route('/api/notificaciones/<int:id>/leer', methods=['POST'])
@login_required
@superadmin_required
def api_marcar_leida(id):
    notif = Notificacion.query.get_or_404(id)
    notif.leida = True
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/api/notificaciones/marcar_todas', methods=['POST'])
@login_required
@superadmin_required
def api_marcar_todas_leidas():
    Notificacion.query.update({Notificacion.leida: True})
    db.session.commit()
    return jsonify({'success': True})