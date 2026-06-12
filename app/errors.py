from flask import jsonify, render_template, request
from .extensions import db

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Recurso no encontrado'}), 404
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Error interno del servidor'}), 500
        return render_template('500.html'), 500