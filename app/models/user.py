from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
import uuid

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=True)
    username = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(200))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    session_token = db.Column(db.String(100), default=lambda: str(uuid.uuid4()))
    is_active = db.Column(db.Boolean, default=True)
    
    role = db.relationship('Role', backref='users')
    agenda = db.relationship('UserAgenda', back_populates='user', cascade='all, delete-orphan')
    asistencias = db.relationship('Asistencia', back_populates='user', cascade='all, delete-orphan')
    logs = db.relationship('ActivityLog', back_populates='user', cascade='all, delete-orphan')
    notificaciones = db.relationship('Notificacion', back_populates='usuario', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.id)

class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.relationship('Permission', secondary='role_permissions', backref='roles')

class Permission(db.Model):
    __tablename__ = 'permission'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    codename = db.Column(db.String(100), unique=True, nullable=False)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
)