from flask import request, session, redirect, url_for, flash, current_app
from flask_login import current_user, logout_user
from .extensions import db
from .models import User, Role, Permission
from datetime import datetime

# ==================================================
# LISTA ACTUALIZADA DE ENDPOINTS PÚBLICOS
# ==================================================
public_endpoints = [
    # Blueprint 'public'
    'public.index',
    'public.ver_actividades',
    'public.ver_conferencistas',
    'public.detalle',
    'public.api_actividades',

    # Blueprint 'auth'
    'auth.login',
    'auth.register_form',
    'auth.register_send_code',
    'auth.register_verify',
    'auth.forgot_password',
    'auth.reset_password',
    'auth.forgot_password_student',
    'auth.reset_password_student',

    # Archivos estáticos
    'static'
]

def session_checker():
    # Si el endpoint actual está en la lista de públicos, no hacer nada
    if request.endpoint in public_endpoints:
        return

    # Verificar autenticación
    if not current_user.is_authenticated:
        flash("Por favor inicia sesión para acceder a esta página.", "warning")
        return redirect(url_for('auth.login'))

    # Verificar que el usuario aún existe en la base de datos
    user = db.session.get(User, current_user.get_id())
    if user is None:
        logout_user()
        session.clear()
        flash("Tu sesión ha expirado. Inicia sesión nuevamente.", "warning")
        return redirect(url_for('auth.login'))

    # Verificar token de sesión
    stored_token = session.get('_user_session_token')
    if not stored_token or stored_token != user.session_token:
        logout_user()
        session.clear()
        flash("Tu sesión ha expirado. Inicia sesión nuevamente.", "warning")
        return redirect(url_for('auth.login'))

def inject_jornada_actual():
    año_actual = datetime.now().year
    jornada_actual = año_actual - 2013
    return dict(current_jornada=jornada_actual, current_jornada_year=año_actual)

def init_roles_and_permissions(app):
    """Inicializa roles y permisos, y crea superadmin por defecto."""
    with app.app_context():
        permisos = [
            ('Ver actividades', 'view_activities'),
            ('Guardar agenda propia', 'save_agenda'),
            ('Gestionar actividades', 'manage_activities'),
            ('Ver dashboard', 'view_dashboard'),
            ('Gestionar usuarios', 'manage_users'),
            ('Exportar datos', 'export_data')
        ]
        for name, codename in permisos:
            if not Permission.query.filter_by(codename=codename).first():
                db.session.add(Permission(name=name, codename=codename))
        db.session.commit()

        roles_data = {
            'visitante': ['view_activities'],
            'estudiante': ['view_activities', 'save_agenda'],
            'admin': ['view_activities', 'save_agenda', 'manage_activities', 'view_dashboard', 'export_data'],
            'superadmin': ['view_activities', 'save_agenda', 'manage_activities', 'manage_users', 'view_dashboard', 'export_data']
        }
        for role_name, perm_codenames in roles_data.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name)
                db.session.add(role)
                db.session.commit()
            for codename in perm_codenames:
                perm = Permission.query.filter_by(codename=codename).first()
                if perm and perm not in role.permissions:
                    role.permissions.append(perm)
            db.session.commit()

        # Crear superadmin por defecto (usando el mail configurado)
        admin_email = app.config.get('MAIL_USERNAME')
        if admin_email:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(username='Administrador', email=admin_email)
                admin.set_password('admin123')
                superadmin_role = Role.query.filter_by(name='superadmin').first()
                admin.role = superadmin_role
                db.session.add(admin)
                db.session.commit()
                print("✅ Superadmin creado con email:", admin_email)
            else:
                if not admin.role or admin.role.name != 'superadmin':
                    admin.role = Role.query.filter_by(name='superadmin').first()
                    db.session.commit()
                    print("✅ Usuario actualizado a superadmin")