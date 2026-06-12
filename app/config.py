import os
from datetime import timedelta

# Obtener la ruta absoluta del directorio actual (app/)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-cambiar-en-produccion')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Ruta absoluta para la carpeta de subidas (en Render los archivos se pierden al reiniciar, pero sirve para pruebas)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Sesión
    REMEMBER_COOKIE_DURATION = timedelta(seconds=0)
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'mi_app_sesion'
    
    # Correo
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    @staticmethod
    def init_app(app):
        # Crear carpeta de uploads si no existe (solo útil en desarrollo, en Render se hace en el código)
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///database.db'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    # Propiedad para convertir la URL de PostgreSQL si es necesario
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            # Render usa 'postgres://', SQLAlchemy necesita 'postgresql://'
            return db_url.replace('postgres://', 'postgresql://', 1)
        return 'sqlite:///database.db'  # Fallback (no debería ocurrir en producción)
    
    @classmethod
    def init_app(cls, app):
        import logging
        from logging.handlers import RotatingFileHandler
        if not app.debug:
            handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
            handler.setLevel(logging.INFO)
            app.logger.addHandler(handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}