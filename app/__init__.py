import os
from flask import Flask
from .config import config
from .extensions import db, mail, login_manager, migrate
from .models import User
from .routes import register_blueprints

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Inicializar extensiones
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # ==================================================
    # IMPORTANTE: user_loader para Flask-Login
    # ==================================================
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # ==================================================
    # Crear carpetas necesarias (uploads)
    # ==================================================
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"✅ Carpeta creada: {upload_folder}")
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Context processor
    from .utils import inject_jornada_actual
    app.context_processor(inject_jornada_actual)
    
    # Before request: verificar sesión
    from .utils import session_checker
    app.before_request(session_checker)
    
    # Manejadores de errores
    from .errors import register_error_handlers
    register_error_handlers(app)
    
    return app

# Importar modelos para Alembic
from .models import user, actividad, agenda, asistencia, notificacion