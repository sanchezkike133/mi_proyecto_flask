# decorators.py
from functools import wraps
from flask import flash, redirect, url_for, session, make_response
from flask_login import current_user

def permission_required(permission_codename):
    """
    Decorador genérico para verificar si el usuario autenticado tiene un permiso específico.
    Uso: @permission_required('manage_activities')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Si no está autenticado, redirigir al login
            if not current_user.is_authenticated:
                flash("Debes iniciar sesión para acceder a esta página.", "warning")
                return redirect(url_for('login'))
            
            # Verificar que el usuario tenga un rol asignado
            if not hasattr(current_user, 'role') or not current_user.role:
                flash("Tu cuenta no tiene un rol válido. Contacta al administrador.", "error")
                return redirect(url_for('logout'))
            
            # Obtener los códigos de permiso del rol del usuario
            user_permissions = [p.codename for p in current_user.role.permissions]
            
            # Comprobar si el permiso requerido está en la lista
            if permission_codename not in user_permissions:
                flash("No tienes permiso para realizar esta acción.", "error")
                return redirect(url_for('ver_actividades'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorador específico para acciones que requieren permisos de administración
    (gestionar actividades). Equivalente a @permission_required('manage_activities')
    """
    return permission_required('manage_activities')(f)


def superadmin_required(f):
    """
    Decorador para acciones que solo puede realizar un superadministrador
    (gestionar usuarios, cambiar roles). Equivalente a @permission_required('manage_users')
    """
    return permission_required('manage_users')(f)


def no_cache(view):
    """
    Decorador para deshabilitar caché del navegador en rutas sensibles
    (dashboard, edición, etc.)
    """
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view