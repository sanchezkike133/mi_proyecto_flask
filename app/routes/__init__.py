def register_blueprints(app):
    from .public import bp as public_bp
    from .auth import bp as auth_bp
    from .agenda import bp as agenda_bp
    from .admin import bp as admin_bp
    from .superadmin import bp as superadmin_bp
    from .api import bp as api_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(agenda_bp, url_prefix='/agenda')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(superadmin_bp, url_prefix='/superadmin')
    app.register_blueprint(api_bp, url_prefix='/api')