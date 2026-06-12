import os
from app import create_app
from app.extensions import db
from app.utils import init_roles_and_permissions

# Obtener el entorno desde variable de entorno (por defecto 'development')
env = os.getenv('FLASK_CONFIG', 'default')
app = create_app(env)

if __name__ == '__main__':
    # Solo ejecutar creación de tablas y roles si NO estamos en producción
    # (Render usará gunicorn y wsgi.py, no este archivo)
    if env != 'production':
        with app.app_context():
            db.create_all()
            init_roles_and_permissions(app)
        # Modo debug solo en desarrollo
        debug = (env == 'development')
    else:
        debug = False

    app.run(host='0.0.0.0', port=5000, debug=debug)