from functools import wraps
from flask import flash, redirect, url_for, make_response
from flask_login import current_user

def permission_required(permission_codename):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Debes iniciar sesión para acceder.", "warning")
                return redirect(url_for('auth.login'))
            if not current_user.role:
                flash("Usuario sin rol asignado.", "error")
                return redirect(url_for('auth.logout'))
            if not any(p.codename == permission_codename for p in current_user.role.permissions):
                flash("No tienes permiso para esta acción.", "error")
                return redirect(url_for('public.ver_actividades'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permission_required('manage_activities')(f)

def superadmin_required(f):
    return permission_required('manage_users')(f)

def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view