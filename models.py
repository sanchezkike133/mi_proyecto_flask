# models.py
# Importaciones necesarias
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

# Instancia de SQLAlchemy (se inicializará en app.py con init_app)
db = SQLAlchemy()

# =========================
# MODELOS PARA RBAC (ROLES Y PERMISOS)
# =========================

class Permission(db.Model):
    """Permisos individuales (ej: 'view_activities', 'manage_users')"""
    __tablename__ = 'permission'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)      # Nombre legible
    codename = db.Column(db.String(100), unique=True, nullable=False)  # Identificador técnico

    def __repr__(self):
        return f'<Permission {self.codename}>'


class Role(db.Model):
    """Roles que agrupan permisos (admin, estudiante, visitante, etc.)"""
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    # Relación muchos a muchos con Permission a través de tabla intermedia
    permissions = db.relationship('Permission', secondary='role_permissions', backref='roles')

    def __repr__(self):
        return f'<Role {self.name}>'


# Tabla intermedia para la relación muchos a muchos entre Role y Permission
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)


# =========================
# MODELO DE USUARIO (con roles y sesión)
# =========================

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    session_token = db.Column(db.String(100), default=lambda: str(uuid.uuid4()))
    
    # Relación con Role
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, codename):
        """Verifica si el usuario tiene un permiso específico a través de su rol"""
        if not self.role:
            return False
        return any(p.codename == codename for p in self.role.permissions)
    
    def __repr__(self):
        return f'<User {self.email}>'


# =========================
# MODELO DE ACTIVIDAD (igual al original)
# =========================

class Actividad(db.Model):
    __tablename__ = 'actividad'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    day = db.Column(db.String(50))
    category = db.Column(db.String(100))
    date = db.Column(db.String(100))
    start_time = db.Column(db.String(50))
    end_time = db.Column(db.String(50))
    speaker = db.Column(db.String(200))
    venue = db.Column(db.String(200))
    description = db.Column(db.Text)
    image = db.Column(db.String(300))
    career = db.Column(db.String(200))
    institution = db.Column(db.String(200))
    speaker_email = db.Column(db.String(200))
    speaker_phone = db.Column(db.String(50))
    academic_degree = db.Column(db.String(100))
    specialty = db.Column(db.String(200))
    experience = db.Column(db.String(200))
    social = db.Column(db.String(300))
    bio = db.Column(db.Text)

    def __repr__(self):
        return f'<Actividad {self.title}>'


# =========================
# AGENDA PERSISTENTE PARA USUARIOS AUTENTICADOS
# =========================

class UserAgenda(db.Model):
    """Relación muchos a muchos entre User y Actividad para guardar agenda personal"""
    __tablename__ = 'user_agenda'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=False)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='agenda_items')
    actividad = db.relationship('Actividad', backref='guardada_por_usuarios')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'actividad_id', name='unique_user_actividad'),)


# =========================
# AUDITORÍA DE ACCIONES DE ADMINISTRADORES
# =========================

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)   # 'crear', 'editar', 'eliminar'
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='logs')
    actividad = db.relationship('Actividad', backref='logs')


# =========================
# RECUPERACIÓN DE CONTRASEÑA (token)
# =========================

class PasswordReset(db.Model):
    __tablename__ = 'password_reset'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    token = db.Column(db.String(200), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)