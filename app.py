from flask import Flask, render_template, redirect, url_for, request, flash, session, make_response, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from functools import wraps
import os
from datetime import datetime, timedelta
import uuid
import random
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from sqlalchemy import or_
import qrcode

# =========================
# CONFIGURACIÓN DE LA APLICACIÓN
# =========================
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_super_segura_cambiar_en_produccion')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Configuración de sesión
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=0)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'mi_app_sesion'

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'sanchezkike133@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'rhyexzgyposwfucd')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."
login_manager.login_message_category = "warning"

# =========================
# MODELOS
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=True)
    username = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(200))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref='users')
    session_token = db.Column(db.String(100), default=lambda: str(uuid.uuid4()))
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.relationship('Permission', secondary='role_permissions', backref='roles')

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    codename = db.Column(db.String(100), unique=True, nullable=False)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
)

class MatriculaValida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Actividad(db.Model):
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
    event_type = db.Column(db.String(20), default='jornada')
    jornada_numero = db.Column(db.Integer, nullable=True)
    qr_token = db.Column(db.String(100), unique=True, nullable=True)
    qr_generated_at = db.Column(db.DateTime, nullable=True)

class UserAgenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=False)
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='agenda')
    actividad = db.relationship('Actividad')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100))
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100))
    token = db.Column(db.String(200), unique=True)
    expires_at = db.Column(db.DateTime)

class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

class Asistencia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividad.id'), nullable=False)
    fecha_hora_registro = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='asistencias')
    actividad = db.relationship('Actividad', backref='asistencias')

# ===== MODELO NOTIFICACIONES =====
class Notificacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(50), default='info')
    leida = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    usuario = db.relationship('User', backref='notificaciones')

# =========================
# DECORADORES DE PERMISOS (sin cambios)
# =========================
def permission_required(permission_codename):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Debes iniciar sesión para acceder.", "warning")
                return redirect(url_for('login'))
            if not current_user.role:
                flash("Usuario sin rol asignado.", "error")
                return redirect(url_for('logout'))
            if not any(p.codename == permission_codename for p in current_user.role.permissions):
                flash("No tienes permiso para esta acción.", "error")
                return redirect(url_for('ver_actividades'))
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

# =========================
# LOGIN MANAGER
# =========================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# =========================
# LISTA DE RUTAS PÚBLICAS
# =========================
public_endpoints = [
    'index', 'ver_actividades', 'ver_conferencistas', 'detalle',
    'login', 'register_form', 'register_send_code', 'register_verify',
    'forgot_password', 'reset_password', 'forgot_password_student', 'reset_password_student',
    'mi_agenda', 'api_actividades', 'static'
]

@app.before_request
def verificar_sesion():
    if request.endpoint in public_endpoints:
        return
    if not current_user.is_authenticated:
        flash("Por favor inicia sesión para acceder a esta página.", "warning")
        return redirect(url_for('login'))
    user = User.query.get(current_user.get_id())
    if user is None:
        logout_user()
        session.clear()
        flash("Tu sesión ha expirado. Inicia sesión nuevamente.", "warning")
        return redirect(url_for('login'))
    stored_token = session.get('_user_session_token')
    if not stored_token or stored_token != user.session_token:
        logout_user()
        session.clear()
        flash("Tu sesión ha expirado. Inicia sesión nuevamente.", "warning")
        return redirect(url_for('login'))

# =========================
# CONTEXT PROCESSOR
# =========================
@app.context_processor
def inject_jornada_actual():
    año_actual = datetime.now().year
    jornada_actual = año_actual - 2013
    return dict(current_jornada=jornada_actual, current_jornada_year=año_actual)

# =========================
# UTILIDADES DE CORREO (sin cambios)
# =========================
def send_email_code(email, code, student_name):
    school_name = "UES 'San José del Rincón'"
    event_name = f"{inject_jornada_actual()['current_jornada']}va Jornada Académica y Cultural {inject_jornada_actual()['current_jornada_year']}"
    year = datetime.now().year
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Verificación de registro</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f5; margin:0; padding:0; }}
            .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .header {{ background: #008000; padding: 20px; text-align: center; color: white; }}
            .content {{ padding: 30px; }}
            .code {{ font-size: 32px; font-weight: bold; background: #f0fdf4; display: inline-block; padding: 12px 24px; border-radius: 12px; letter-spacing: 4px; color: #008000; margin: 20px 0; }}
            .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{school_name}</h1>
                <p>{event_name}</p>
            </div>
            <div class="content">
                <h2>Hola <strong>{student_name}</strong></h2>
                <p>Tu código de verificación para completar el registro es:</p>
                <div style="text-align: center;"><span class="code">{code}</span></div>
                <p>Válido por <strong>5 minutos</strong>.</p>
                <p>Si no solicitaste este registro, ignora este mensaje.</p>
            </div>
            <div class="footer">
                &copy; {year} {school_name} - Todos los derechos reservados.
            </div>
        </div>
    </body>
    </html>
    """
    msg = Message(f"🔐 Código de verificación - {event_name}",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.html = html_content
    msg.body = f"Hola {student_name},\n\nTu código de verificación es: {code}\n\nVálido por 5 minutos."
    try:
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Error enviando correo: {e}")
        return False

def send_password_reset_code(email, code, student_name):
    school_name = "UES 'San José del Rincón'"
    year = datetime.now().year
    jornada = inject_jornada_actual()['current_jornada']
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Recuperación de contraseña</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f5; margin:0; padding:0; }}
            .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .header {{ background: #008000; padding: 20px; text-align: center; color: white; }}
            .content {{ padding: 30px; }}
            .code {{ font-size: 32px; font-weight: bold; background: #f0fdf4; display: inline-block; padding: 12px 24px; border-radius: 12px; letter-spacing: 4px; color: #008000; margin: 20px 0; }}
            .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{school_name}</h1>
                <p>{jornada}va Jornada Académica y Cultural {year}</p>
            </div>
            <div class="content">
                <h2>Hola <strong>{student_name}</strong></h2>
                <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
                <p>Utiliza el siguiente código:</p>
                <div style="text-align: center;"><span class="code">{code}</span></div>
                <p>Válido por <strong>5 minutos</strong>.</p>
                <p>Si no solicitaste este cambio, ignora este mensaje.</p>
            </div>
            <div class="footer">
                &copy; {year} {school_name} - Todos los derechos reservados.
            </div>
        </div>
    </body>
    </html>
    """
    msg = Message("🔐 Recuperación de contraseña - Jornada Académica",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.html = html_content
    msg.body = f"Hola {student_name},\n\nTu código de recuperación es: {code}\n\nVálido por 5 minutos."
    try:
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Error enviando correo de recuperación: {e}")
        return False

# =========================
# FUNCIÓN PARA GENERAR CÓDIGO QR
# =========================
def generar_imagen_qr(texto):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def registrar_notificacion(mensaje, tipo='info', usuario_id=None):
    notif = Notificacion(mensaje=mensaje, tipo=tipo, usuario_id=usuario_id)
    db.session.add(notif)
    db.session.commit()

# =========================
# RUTAS PÚBLICAS (sin cambios)
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ver_actividades')
def ver_actividades():
    actividades = Actividad.query.all()
    return render_template('ver_actividades.html', actividades=actividades)

@app.route('/conferencistas')
def ver_conferencistas():
    conferencistas = db.session.query(Actividad.speaker,
                                      Actividad.speaker_email,
                                      Actividad.speaker_phone,
                                      Actividad.academic_degree,
                                      Actividad.specialty,
                                      Actividad.experience,
                                      Actividad.social,
                                      Actividad.bio,
                                      Actividad.image,
                                      Actividad.title,
                                      Actividad.day,
                                      Actividad.start_time).filter(Actividad.speaker.isnot(None)).distinct().all()
    conferencistas_dict = {}
    for c in conferencistas:
        if c[0] not in conferencistas_dict:
            conferencistas_dict[c[0]] = {
                'nombre': c[0], 'email': c[1], 'telefono': c[2], 'grado': c[3],
                'especialidad': c[4], 'experiencia': c[5], 'social': c[6], 'bio': c[7],
                'imagen': c[8], 'actividades': []
            }
        if c[9]:
            conferencistas_dict[c[0]]['actividades'].append({
                'titulo': c[9], 'dia': c[10], 'hora': c[11]
            })
    return render_template('conferencistas.html', conferencistas=conferencistas_dict.values())

@app.route('/detalle/<int:id>')
def detalle(id):
    actividad = Actividad.query.get_or_404(id)
    return render_template('detalle.html', actividad=actividad)

@app.route('/api/actividades')
def api_actividades():
    actividades = Actividad.query.all()
    return jsonify([
        {
            'id': a.id,
            'title': a.title,
            'day': a.day,
            'category': a.category,
            'date': a.date,
            'start_time': a.start_time,
            'end_time': a.end_time,
            'speaker': a.speaker,
            'venue': a.venue,
            'description': a.description,
            'image': a.image,
            'event_type': a.event_type,
            'jornada_numero': a.jornada_numero,
            'qr_token': a.qr_token,
            'career': a.career,
            'institution': a.institution,
            'speaker_email': a.speaker_email,
            'speaker_phone': a.speaker_phone,
            'academic_degree': a.academic_degree,
            'specialty': a.specialty,
            'experience': a.experience,
            'social': a.social,
            'bio': a.bio
        }
        for a in actividades
    ])

# =========================
# REGISTRO, LOGIN, RECUPERACIÓN (sin cambios relevantes)
# =========================
@app.route('/register', methods=['GET'])
def register_form():
    if current_user.is_authenticated:
        return redirect(url_for('ver_actividades'))
    return render_template('register.html')

@app.route('/register/send-code', methods=['POST'])
def register_send_code():
    if current_user.is_authenticated:
        return jsonify({'error': 'Ya estás autenticado'}), 400
    student_id = request.form.get('student_id')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm = request.form.get('confirm_password')
    if not all([student_id, full_name, email, password, confirm]):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
    if password != confirm:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400
    if len(password) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    matricula_valida = MatriculaValida.query.filter_by(student_id=student_id).first()
    if not matricula_valida:
        return jsonify({'error': 'Matrícula no autorizada'}), 400
    if User.query.filter_by(student_id=student_id).first():
        return jsonify({'error': 'Ya existe una cuenta con esa matrícula'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El correo ya está registrado'}), 400
    code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=5)
    verif = VerificationCode(phone=email, code=code, expires_at=expires, used=False)
    db.session.add(verif)
    db.session.commit()
    success = send_email_code(email, code, full_name)
    if not success:
        return jsonify({'error': 'No se pudo enviar el código de verificación.'}), 500
    session['pending_registration'] = {
        'student_id': student_id,
        'full_name': full_name,
        'email': email,
        'phone': phone or '',
        'password': password
    }
    session['verify_identifier'] = email
    return jsonify({'success': True, 'message': 'Código enviado a tu correo'})

@app.route('/register/verify', methods=['POST'])
def register_verify():
    if current_user.is_authenticated:
        return jsonify({'error': 'Ya estás autenticado'}), 400
    code = request.form.get('code')
    identifier = session.get('verify_identifier')
    pending = session.get('pending_registration')
    if not identifier or not pending:
        return jsonify({'error': 'No hay registro pendiente'}), 400
    record = VerificationCode.query.filter_by(phone=identifier, code=code, used=False).first()
    if not record or record.expires_at < datetime.utcnow():
        return jsonify({'error': 'Código inválido o expirado'}), 400
    record.used = True
    db.session.commit()
    estudiante_role = Role.query.filter_by(name='estudiante').first()
    if not estudiante_role:
        return jsonify({'error': 'Error de configuración de roles'}), 500
    user = User(
        student_id=pending['student_id'],
        username=pending['full_name'],
        email=pending['email'],
        phone=pending.get('phone'),
        role=estudiante_role,
        is_active=True
    )
    user.set_password(pending['password'])
    db.session.add(user)
    db.session.commit()
    session.pop('pending_registration', None)
    session.pop('verify_identifier', None)
    return jsonify({'success': True, 'message': 'Registro exitoso. Ahora inicia sesión.'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        if identifier.isdigit() and len(identifier) >= 6:
            user = User.query.filter_by(student_id=identifier).first()
        else:
            user = User.query.filter_by(email=identifier).first()
        if user and user.check_password(password) and user.is_active:
            user.session_token = str(uuid.uuid4())
            db.session.commit()
            login_user(user)
            session['_user_session_token'] = user.session_token
            flash(f"¡Bienvenido {user.username}!", "success")
            if user.role and any(p.codename == 'view_dashboard' for p in user.role.permissions):
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('ver_actividades'))
        else:
            flash("Credenciales incorrectas o cuenta inactiva.", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    if current_user.is_authenticated:
        current_user.session_token = str(uuid.uuid4())
        db.session.commit()
    logout_user()
    session.clear()
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user and user.role and user.role.name in ['admin', 'superadmin']:
            token = str(uuid.uuid4())
            expires = datetime.utcnow() + timedelta(minutes=15)
            reset = PasswordReset(email=email, token=token, expires_at=expires)
            db.session.add(reset)
            db.session.commit()
            reset_link = url_for('reset_password', token=token, _external=True)
            msg = Message("Recuperación de contraseña - Administrador",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Hola,\n\nHaz clic para restablecer tu contraseña: {reset_link}\n\nVálido por 15 minutos."
            try:
                mail.send(msg)
                flash("Correo enviado.", "success")
            except Exception as e:
                app.logger.error(f"Error: {e}")
                flash("Error al enviar correo.", "error")
        else:
            flash("El correo no corresponde a un administrador.", "error")
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset = PasswordReset.query.filter_by(token=token).first()
    if not reset or reset.expires_at < datetime.utcnow():
        flash("Token inválido o expirado.", "error")
        return redirect(url_for('login'))
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form.get('confirm_password')
        if not password or password != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for('reset_password', token=token))
        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return redirect(url_for('reset_password', token=token))
        user = User.query.filter_by(email=reset.email).first()
        if user:
            user.set_password(password)
            db.session.commit()
        db.session.delete(reset)
        db.session.commit()
        flash("Contraseña actualizada. Inicia sesión.", "success")
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/forgot-password-student', methods=['GET', 'POST'])
def forgot_password_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        email = request.form.get('email')
        user = User.query.filter_by(student_id=student_id, email=email).first()
        if user and user.role and user.role.name == 'estudiante':
            code = str(random.randint(100000, 999999))
            expires = datetime.utcnow() + timedelta(minutes=5)
            verif = VerificationCode(phone=email, code=code, expires_at=expires, used=False)
            db.session.add(verif)
            db.session.commit()
            success = send_password_reset_code(email, code, user.username or "estudiante")
            if success:
                session['reset_email'] = email
                flash("Se ha enviado un código de verificación a tu correo.", "success")
                return redirect(url_for('reset_password_student'))
            else:
                flash("Error al enviar el código.", "error")
        else:
            flash("No se encontró una cuenta de estudiante con esos datos.", "error")
        return redirect(url_for('login'))
    return render_template('forgot_password_student.html')

@app.route('/reset-password-student', methods=['GET', 'POST'])
def reset_password_student():
    if request.method == 'POST':
        code = request.form.get('code')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        email = session.get('reset_email')
        if not email:
            flash("No hay solicitud de recuperación activa.", "error")
            return redirect(url_for('forgot_password_student'))
        if not code or not password or not confirm:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for('reset_password_student'))
        if password != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for('reset_password_student'))
        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return redirect(url_for('reset_password_student'))
        record = VerificationCode.query.filter_by(phone=email, code=code, used=False).first()
        if not record or record.expires_at < datetime.utcnow():
            flash("Código inválido o expirado.", "error")
            return redirect(url_for('reset_password_student'))
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            record.used = True
            db.session.commit()
            session.pop('reset_email', None)
            flash("Contraseña actualizada. Inicia sesión.", "success")
            return redirect(url_for('login'))
        else:
            flash("Usuario no encontrado.", "error")
            return redirect(url_for('forgot_password_student'))
    if not session.get('reset_email'):
        flash("No hay una solicitud de recuperación activa.", "warning")
        return redirect(url_for('forgot_password_student'))
    return render_template('reset_password_code.html')

# =========================
# AGENDA PERSONAL (CON BASE DE DATOS)
# =========================
@app.route('/mi_agenda')
@login_required
def mi_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        flash("Esta sección es solo para estudiantes.", "warning")
        return redirect(url_for('ver_actividades'))
    return render_template('mi_agenda.html')

@app.route('/api/agenda', methods=['GET'])
@login_required
def api_get_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        return jsonify({'error': 'No autorizado'}), 403
    agenda_ids = [ua.actividad_id for ua in UserAgenda.query.filter_by(user_id=current_user.id).all()]
    return jsonify({'saved_ids': agenda_ids})

@app.route('/api/agenda/toggle', methods=['POST'])
@login_required
def api_toggle_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json()
    actividad_id = data.get('actividad_id')
    if not actividad_id:
        return jsonify({'error': 'Falta actividad_id'}), 400
    actividad = Actividad.query.get(actividad_id)
    if not actividad:
        return jsonify({'error': 'Actividad no existe'}), 404

    existe = UserAgenda.query.filter_by(user_id=current_user.id, actividad_id=actividad_id).first()
    if existe:
        db.session.delete(existe)
        db.session.commit()
        return jsonify({'saved': False, 'message': 'Eliminado de tu agenda'})
    else:
        nueva = UserAgenda(user_id=current_user.id, actividad_id=actividad_id)
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'saved': True, 'message': 'Agregado a tu agenda'})

# =========================
# FUNCIÓN MEJORADA PARA GENERAR PDF (DISEÑO PROFESIONAL)
# =========================
def generar_pdf_actividades(actividades, titulo_principal, subtitulo, columnas, mostrar_tipo_jornada=True):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.8*cm, bottomMargin=1.5*cm)
    story = []
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#008000'),
        alignment=1,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        alignment=1,
        spaceAfter=20
    )
    estilo_fecha = ParagraphStyle(
        'Fecha',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=2,
        spaceAfter=12
    )
    estilo_cabecera = ParagraphStyle(
        'CabeceraTabla',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    estilo_celda = ParagraphStyle(
        'CeldaTabla',
        parent=styles['Normal'],
        fontSize=9,
        leading=12
    )

    story.append(Paragraph(titulo_principal, estilo_titulo))
    story.append(Paragraph(subtitulo, estilo_subtitulo))
    story.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_fecha))
    story.append(Spacer(1, 0.3*cm))

    cols = columnas.copy()
    if mostrar_tipo_jornada:
        cols.insert(0, {'key': 'tipo', 'label': 'Tipo', 'width': 2.5*cm})

    total_width = 0
    for col in cols:
        if 'width' not in col:
            col['width'] = 3.5*cm
        total_width += col['width']
    page_width = landscape(A4)[0] - 3*cm
    if total_width < page_width:
        factor = page_width / total_width
        for col in cols:
            col['width'] = col['width'] * factor

    header_cells = [Paragraph(col['label'], estilo_cabecera) for col in cols]
    data_table = [header_cells]

    for act in actividades:
        fila = []
        for col in cols:
            if col['key'] == 'tipo':
                if act.event_type == 'jornada' and act.jornada_numero:
                    tipo_texto = f"{act.jornada_numero}va Jornada"
                elif act.event_type == 'jornada':
                    tipo_texto = "Jornada"
                else:
                    tipo_texto = "Extracurricular"
                fila.append(Paragraph(tipo_texto, estilo_celda))
            else:
                valor = getattr(act, col['key'], '') or ''
                if col['key'] == 'date' and valor:
                    try:
                        fecha_obj = datetime.strptime(valor, '%Y-%m-%d')
                        valor = fecha_obj.strftime('%d/%m/%Y')
                    except:
                        pass
                fila.append(Paragraph(str(valor), estilo_celda))
        data_table.append(fila)

    table = Table(data_table, colWidths=[col['width'] for col in cols], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Documento generado automáticamente por el sistema de la Jornada Académica",
                          ParagraphStyle('Pie', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer

def send_pdf(buffer, filename):
    return Response(buffer, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename={filename}'})

# =========================
# RUTAS DE EXPORTACIÓN PARA ADMINISTRADOR
# =========================
@app.route('/exportar/jornada')
@login_required
@admin_required
def exportar_jornada():
    dia = request.args.get('dia', 'todos').lower()
    query = Actividad.query.filter_by(event_type='jornada')
    if dia != 'todos':
        dia_capitalizado = dia.capitalize()
        query = query.filter_by(day=dia_capitalizado)
    actividades = query.order_by(Actividad.date, Actividad.start_time).all()

    año_actual = datetime.now().year
    jornada_num = año_actual - 2013
    if dia == 'todos':
        titulo = f"{jornada_num}va Jornada Académica y Cultural - Programación completa"
    else:
        titulo = f"{jornada_num}va Jornada Académica - Actividades del {dia.capitalize()}"

    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'date', 'label': 'Fecha', 'width': 2.5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm},
        {'key': 'category', 'label': 'Categoría', 'width': 3*cm}
    ]
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=titulo,
        subtitulo="UES 'San José del Rincón'",
        columnas=columnas,
        mostrar_tipo_jornada=False
    )
    return send_pdf(pdf_buffer, f'jornada_{dia}.pdf')

@app.route('/exportar/generales')
@login_required
@admin_required
def exportar_generales():
    anio = request.args.get('anio', '')
    mes = request.args.get('mes', '')
    dia = request.args.get('dia', '')
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    career = request.args.get('career', '')
    estado = request.args.get('estado', '')

    query = Actividad.query.filter_by(event_type='extra')
    if anio:
        query = query.filter(Actividad.date.like(f'{anio}%'))
    if mes:
        mes_padded = mes.zfill(2)
        query = query.filter(Actividad.date.like(f'%-{mes_padded}-%'))
    if dia:
        dia_padded = dia.zfill(2)
        query = query.filter(Actividad.date.like(f'%-{dia_padded}'))
    if search:
        term = f'%{search}%'
        query = query.filter(or_(Actividad.title.ilike(term), Actividad.speaker.ilike(term)))
    if category:
        query = query.filter(Actividad.category == category)
    if career:
        query = query.filter(Actividad.career == career)

    actividades = query.order_by(Actividad.date, Actividad.start_time).all()
    ahora = datetime.now()
    actividades_filtradas = []
    for a in actividades:
        if a.date and a.start_time:
            try:
                fecha_hora_evento = datetime.strptime(f"{a.date} {a.start_time}", '%Y-%m-%d %H:%M')
                es_activo = fecha_hora_evento > ahora
                if estado == 'activo' and not es_activo:
                    continue
                if estado == 'finalizado' and es_activo:
                    continue
            except:
                pass
        elif estado:
            continue
        actividades_filtradas.append(a)

    if not estado:
        actividades_filtradas = actividades

    titulo = 'Eventos Generales'
    filtros = []
    if search:
        filtros.append(f"Búsqueda: {search}")
    if category:
        filtros.append(f"Categoría: {category}")
    if career:
        filtros.append(f"Dirigido a: {career}")
    if anio:
        filtros.append(f"Año: {anio}")
    if mes:
        filtros.append(f"Mes: {mes}")
    if dia:
        filtros.append(f"Día: {dia}")
    if estado:
        filtros.append(f"Estado: {'Activos' if estado == 'activo' else 'Finalizados'}")
    if filtros:
        titulo += " - " + " | ".join(filtros)

    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'date', 'label': 'Fecha', 'width': 2.5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm}
    ]
    pdf_buffer = generar_pdf_actividades(
        actividades_filtradas,
        titulo_principal=titulo,
        subtitulo="UES 'San José del Rincón'",
        columnas=columnas,
        mostrar_tipo_jornada=True
    )
    return send_pdf(pdf_buffer, 'eventos_generales.pdf')

@app.route('/exportar/generales/fecha/<fecha>')
@login_required
@admin_required
def exportar_generales_fecha(fecha):
    actividades = Actividad.query.filter_by(event_type='extra', date=fecha).order_by(Actividad.start_time).all()
    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm}
    ]
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=f"Eventos Generales - {fecha}",
        subtitulo="UES 'San José del Rincón'",
        columnas=columnas,
        mostrar_tipo_jornada=True
    )
    return send_pdf(pdf_buffer, f'eventos_{fecha}.pdf')

@app.route('/exportar/generales/rango/<desde>/<hasta>')
@login_required
@admin_required
def exportar_generales_rango(desde, hasta):
    actividades = Actividad.query.filter_by(event_type='extra').filter(Actividad.date >= desde, Actividad.date <= hasta).order_by(Actividad.date, Actividad.start_time).all()
    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'date', 'label': 'Fecha', 'width': 2.5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm}
    ]
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=f"Eventos Generales del {desde} al {hasta}",
        subtitulo="UES 'San José del Rincón'",
        columnas=columnas,
        mostrar_tipo_jornada=True
    )
    return send_pdf(pdf_buffer, f'eventos_{desde}_a_{hasta}.pdf')

# =========================
# EXPORTACIÓN PARA ESTUDIANTES
# =========================
@app.route('/mi_agenda/exportar_pdf')
@login_required
def exportar_mi_agenda():
    if not current_user.role or current_user.role.name != 'estudiante':
        flash("Acceso solo para estudiantes", "warning")
        return redirect(url_for('mi_agenda'))

    agenda_items = UserAgenda.query.filter_by(user_id=current_user.id).all()
    actividades = [item.actividad for item in agenda_items]

    if not actividades:
        flash("Tu agenda está vacía. No hay nada para exportar.", "info")
        return redirect(url_for('mi_agenda'))

    columnas = [
        {'key': 'title', 'label': 'Actividad', 'width': 5*cm},
        {'key': 'date', 'label': 'Fecha', 'width': 2.5*cm},
        {'key': 'start_time', 'label': 'Hora inicio', 'width': 2.2*cm},
        {'key': 'end_time', 'label': 'Hora fin', 'width': 2.2*cm},
        {'key': 'speaker', 'label': 'Ponente', 'width': 3.5*cm},
        {'key': 'venue', 'label': 'Sede', 'width': 3*cm}
    ]

    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal="Mi Agenda Personal",
        subtitulo=f"Estudiante: {current_user.username} ({current_user.student_id or current_user.email})",
        columnas=columnas,
        mostrar_tipo_jornada=True
    )
    return send_pdf(pdf_buffer, f'Mi_Agenda_{current_user.id}.pdf')

# =========================
# FUNCIÓN VALIDACIÓN HORARIO
# =========================
def validar_horario_actividad(fecha, start_time, end_time, venue, actividad_id=None):
    from datetime import datetime
    try:
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
    except:
        return False, "Formato de hora inválido."
    min_time = datetime.strptime('08:00', '%H:%M')
    max_time = datetime.strptime('18:00', '%H:%M')
    if start < min_time or end > max_time:
        return False, "El horario debe estar entre 08:00 y 18:00 horas."
    if start >= end:
        return False, "La hora de inicio debe ser anterior a la hora de fin."
    duracion = (end - start).total_seconds() / 60
    if duracion < 10:
        return False, "La actividad debe durar al menos 10 minutos."
    query = Actividad.query.filter(
        Actividad.date == fecha,
        Actividad.venue == venue
    )
    if actividad_id:
        query = query.filter(Actividad.id != actividad_id)
    for act in query:
        act_start = datetime.strptime(act.start_time, '%H:%M')
        act_end = datetime.strptime(act.end_time, '%H:%M')
        if (start < act_end and end > act_start):
            return False, f"Ya existe una actividad en '{venue}' en el horario {act.start_time}-{act.end_time}. Elija otra sede o modifique el horario."
    return True, "OK"

# =========================
# ZONA ADMIN (CRUD + DASHBOARD) CON NOTIFICACIONES
# =========================
@app.route('/dashboard')
@login_required
@permission_required('view_dashboard')
@no_cache
def dashboard():
    actividades = Actividad.query.all()
    usuarios_count = User.query.count()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
    return render_template('dashboard.html', actividades=actividades, usuarios_count=usuarios_count, logs=logs)

@app.route('/admin/api/stats')
@login_required
@admin_required
def admin_api_stats():
    total_actividades = Actividad.query.count()
    total_jornada = Actividad.query.filter_by(event_type='jornada').count()
    total_extra = Actividad.query.filter_by(event_type='extra').count()
    total_usuarios = User.query.count()
    from sqlalchemy import func
    actividad_mas_interes = db.session.query(
        UserAgenda.actividad_id, func.count(UserAgenda.actividad_id).label('count')
    ).group_by(UserAgenda.actividad_id).order_by(func.count(UserAgenda.actividad_id).desc()).first()
    top_actividad = None
    if actividad_mas_interes:
        act = Actividad.query.get(actividad_mas_interes.actividad_id)
        if act:
            top_actividad = {
                'id': act.id,
                'title': act.title,
                'total': actividad_mas_interes.count
            }
    hoy = datetime.now().date()
    proximas = Actividad.query.filter(Actividad.date >= hoy).count()
    return jsonify({
        'total_actividades': total_actividades,
        'total_jornada': total_jornada,
        'total_extra': total_extra,
        'total_usuarios': total_usuarios,
        'actividad_top': top_actividad,
        'proximas_actividades': proximas
    })

@app.route('/nueva_actividad', methods=['GET', 'POST'])
@login_required
@admin_required
@no_cache
def nueva_actividad():
    if request.method == 'POST':
        required_fields = ['title', 'day', 'category', 'date', 'start_time', 'speaker', 'venue']
        for field in required_fields:
            if not request.form.get(field):
                flash(f"El campo {field} es obligatorio.", "error")
                return redirect(url_for('nueva_actividad'))
        fecha = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form.get('end_time')
        venue = request.form['venue']
        if not end_time:
            flash("Debe especificar una hora de fin.", "error")
            return redirect(url_for('nueva_actividad'))
        valido, msg = validar_horario_actividad(fecha, start_time, end_time, venue)
        if not valido:
            flash(msg, "error")
            return redirect(url_for('nueva_actividad'))
        file = request.files.get('imagen')
        image_filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
        fecha_str = request.form.get('date')
        event_type = 'extra'
        jornada_numero = None
        if fecha_str:
            try:
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                if fecha_dt.month == 12:
                    event_type = 'jornada'
                    jornada_numero = fecha_dt.year - 2013
            except:
                pass
        nueva = Actividad(
            title=request.form['title'], day=request.form['day'],
            category=request.form['category'], date=request.form['date'],
            start_time=request.form['start_time'], end_time=request.form.get('end_time'),
            speaker=request.form.get('speaker'), venue=venue,
            description=request.form.get('description'), image=image_filename,
            career=request.form.get('career'), institution=request.form.get('institution'),
            speaker_email=request.form.get('speaker_email'), speaker_phone=request.form.get('speaker_phone'),
            academic_degree=request.form.get('academic_degree'), specialty=request.form.get('specialty'),
            experience=request.form.get('experience'), social=request.form.get('social'),
            bio=request.form.get('bio'),
            event_type=event_type,
            jornada_numero=jornada_numero
        )
        db.session.add(nueva)
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action='crear', actividad_id=nueva.id)
        db.session.add(log)
        db.session.commit()
        registrar_notificacion(f"{current_user.username} creó la actividad '{nueva.title}'", 'success')
        flash("Actividad creada correctamente", "success")
        return redirect(url_for('dashboard'))
    return render_template('nuevo.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@no_cache
def editar(id):
    actividad = Actividad.query.get_or_404(id)
    titulo_original = actividad.title
    if request.method == 'POST':
        required_fields = ['title', 'day', 'category', 'date', 'start_time', 'speaker', 'venue']
        for field in required_fields:
            if not request.form.get(field):
                flash(f"El campo {field} es obligatorio.", "error")
                return redirect(url_for('editar', id=id))
        fecha = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form.get('end_time')
        venue = request.form['venue']
        if not end_time:
            flash("Debe especificar una hora de fin.", "error")
            return redirect(url_for('editar', id=id))
        valido, msg = validar_horario_actividad(fecha, start_time, end_time, venue, actividad_id=id)
        if not valido:
            flash(msg, "error")
            return redirect(url_for('editar', id=id))
        actividad.title = request.form['title']
        actividad.day = request.form['day']
        actividad.category = request.form['category']
        actividad.date = fecha
        actividad.start_time = start_time
        actividad.end_time = end_time
        actividad.speaker = request.form.get('speaker')
        actividad.venue = venue
        actividad.description = request.form.get('description')
        actividad.career = request.form.get('career')
        actividad.institution = request.form.get('institution')
        actividad.speaker_email = request.form.get('speaker_email')
        actividad.speaker_phone = request.form.get('speaker_phone')
        actividad.academic_degree = request.form.get('academic_degree')
        actividad.specialty = request.form.get('specialty')
        actividad.experience = request.form.get('experience')
        actividad.social = request.form.get('social')
        actividad.bio = request.form.get('bio')
        file = request.files.get('imagen')
        if file and allowed_file(file.filename):
            if actividad.image:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], actividad.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            actividad.image = filename
        fecha_str = request.form.get('date')
        if fecha_str:
            try:
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                if fecha_dt.month == 12:
                    actividad.event_type = 'jornada'
                    actividad.jornada_numero = fecha_dt.year - 2013
                else:
                    actividad.event_type = 'extra'
                    actividad.jornada_numero = None
            except:
                pass
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action='editar', actividad_id=actividad.id)
        db.session.add(log)
        db.session.commit()
        registrar_notificacion(f"{current_user.username} editó la actividad '{titulo_original}' (ahora '{actividad.title}')", 'info')
        flash("Actividad actualizada correctamente", "success")
        return redirect(url_for('dashboard'))
    return render_template('editar.html', actividad=actividad)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
@no_cache
def eliminar(id):
    actividad = Actividad.query.get_or_404(id)
    titulo = actividad.title
    if actividad.image:
        path = os.path.join(app.config['UPLOAD_FOLDER'], actividad.image)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(actividad)
    db.session.commit()
    log = ActivityLog(user_id=current_user.id, action='eliminar', actividad_id=id)
    db.session.add(log)
    db.session.commit()
    registrar_notificacion(f"{current_user.username} eliminó la actividad '{titulo}'", 'danger')
    flash("Actividad eliminada correctamente", "warning")
    return redirect(url_for('dashboard'))

# =========================
# API DE GESTIÓN DE USUARIOS (CON PROTECCIÓN PARA SUPERADMIN) + NOTIFICACIONES
# =========================
@app.route('/admin/api/usuarios')
@login_required
@superadmin_required
def api_listar_usuarios():
    usuarios = User.query.all()
    return jsonify([{
        'id': u.id,
        'student_id': u.student_id,
        'username': u.username,
        'email': u.email,
        'phone': u.phone or '',
        'role_name': u.role.name if u.role else 'sin_rol',
        'is_active': u.is_active
    } for u in usuarios])

@app.route('/admin/api/usuario/<int:id>')
@login_required
@superadmin_required
def api_obtener_usuario(id):
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone or '',
        'role_name': user.role.name if user.role else 'estudiante',
        'is_active': user.is_active
    })

@app.route('/admin/api/usuario/<int:id>', methods=['PUT'])
@login_required
@superadmin_required
def api_actualizar_usuario(id):
    user = User.query.get_or_404(id)
    if user.role and user.role.name == 'superadmin':
        data = request.get_json()
        if 'is_active' in data:
            return jsonify({'error': 'No se puede cambiar el estado de un superadministrador'}), 403
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data and data['role'] != 'superadmin':
            return jsonify({'error': 'No se puede cambiar el rol de un superadministrador'}), 403
        if 'new_password' in data and data['new_password'] and len(data['new_password']) >= 6:
            user.set_password(data['new_password'])
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action=f'edit_user_{id}', actividad_id=None)
        db.session.add(log)
        db.session.commit()
        registrar_notificacion(f"{current_user.username} actualizó los datos del usuario '{user.username}' (ID {id})", 'info')
        return jsonify({'message': 'Usuario superadmin actualizado correctamente'})
    else:
        data = request.get_json()
        cambios = []
        if 'username' in data and data['username'] != user.username:
            user.username = data['username']
            cambios.append("nombre")
        if 'email' in data and data['email'] != user.email:
            user.email = data['email']
            cambios.append("email")
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            new_role = Role.query.filter_by(name=data['role']).first()
            if new_role and new_role != user.role:
                user.role = new_role
                cambios.append("rol")
        if 'new_password' in data and data['new_password'] and len(data['new_password']) >= 6:
            user.set_password(data['new_password'])
            cambios.append("contraseña")
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            cambios.append(f"estado a {'activo' if user.is_active else 'inactivo'}")
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action=f'edit_user_{id}', actividad_id=None)
        db.session.add(log)
        db.session.commit()
        if cambios:
            registrar_notificacion(f"{current_user.username} modificó al usuario '{user.username}' (cambios: {', '.join(cambios)})", 'info')
        return jsonify({'message': 'Usuario actualizado correctamente'})

# =========================
# FUNCIÓN ELIMINAR USUARIO CORREGIDA (con eliminación en cascada)
# =========================
@app.route('/admin/api/usuario/<int:id>', methods=['DELETE'])
@login_required
@superadmin_required
def api_eliminar_usuario(id):
    user = User.query.get_or_404(id)
    
    # Protecciones
    if user.id == current_user.id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 403
    if user.role and user.role.name == 'superadmin':
        return jsonify({'error': 'No puedes eliminar un superadministrador'}), 403
    
    nombre = user.username
    email = user.email
    
    try:
        # Eliminar dependencias en cascada (para evitar errores de integridad referencial)
        # 1. Eliminar agenda del usuario (UserAgenda)
        UserAgenda.query.filter_by(user_id=user.id).delete()
        # 2. Eliminar logs de actividad (ActivityLog)
        ActivityLog.query.filter_by(user_id=user.id).delete()
        # 3. Eliminar asistencias (Asistencia)
        Asistencia.query.filter_by(user_id=user.id).delete()
        # 4. Eliminar notificaciones asociadas (Notificacion)
        Notificacion.query.filter_by(usuario_id=user.id).delete()
        # 5. Eliminar códigos de verificación (VerificationCode) si están asociados al email/phone (opcional, pero limpio)
        VerificationCode.query.filter_by(phone=user.email).delete()
        # 6. Eliminar reseteos de contraseña (PasswordReset)
        PasswordReset.query.filter_by(email=user.email).delete()
        
        # Finalmente eliminar el usuario
        db.session.delete(user)
        db.session.commit()
        
        # Registrar notificación y log
        registrar_notificacion(f"{current_user.username} eliminó al usuario '{nombre}' (ID {id}, email {email})", 'danger')
        log = ActivityLog(user_id=current_user.id, action=f'delete_user_{id}', actividad_id=None)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': f'Usuario {nombre} eliminado correctamente'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al eliminar usuario {id}: {str(e)}")
        return jsonify({'error': f'Error al eliminar usuario: {str(e)}'}), 500

# =========================
# RESTO DE ENDPOINTS (CREAR_ADMIN, INTERESADOS, QR, ASISTENCIAS, NOTIFICACIONES, etc.)
# =========================
@app.route('/admin/api/crear_admin', methods=['POST'])
@login_required
@superadmin_required
def api_crear_admin():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password or len(password) < 6:
        return jsonify({'error': 'Datos inválidos'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado'}), 400
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        return jsonify({'error': 'Rol admin no existe'}), 500
    new_admin = User(username=username, email=email, role=admin_role, is_active=True)
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()
    log = ActivityLog(user_id=current_user.id, action=f'crear_admin_{new_admin.id}', actividad_id=None)
    db.session.add(log)
    db.session.commit()
    registrar_notificacion(f"{current_user.username} creó un nuevo administrador: '{username}'", 'success')
    return jsonify({'message': f'Administrador {username} creado correctamente'})

@app.route('/admin/api/actividad/<int:id>/interesados')
@login_required
@admin_required
def api_actividad_interesados(id):
    actividad = Actividad.query.get_or_404(id)
    agenda_items = UserAgenda.query.filter_by(actividad_id=id).all()
    estudiantes = []
    for item in agenda_items:
        user = item.user
        if user.role and user.role.name == 'estudiante':
            estudiantes.append({
                'id': user.id,
                'student_id': user.student_id or 'N/A',
                'username': user.username or 'Sin nombre',
                'email': user.email,
                'phone': user.phone or ''
            })
    return jsonify({
        'actividad_id': id,
        'titulo': actividad.title,
        'total': len(estudiantes),
        'estudiantes': estudiantes
    })

# =========================
# RUTAS PARA CÓDIGOS QR Y ASISTENCIA (sin cambios)
# =========================
@app.route('/admin/actividad/<int:id>/qr/generar', methods=['POST'])
@login_required
@admin_required
def generar_qr_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    ahora = datetime.now()
    fecha_hora_inicio = datetime.strptime(f"{actividad.date} {actividad.start_time}", '%Y-%m-%d %H:%M')
    if fecha_hora_inicio < ahora:
        return jsonify({'error': 'No se puede generar QR para actividades que ya comenzaron o terminaron.'}), 400
    if actividad.qr_token:
        return jsonify({'error': 'Esta actividad ya tiene un código QR generado.'}), 400
    token = str(uuid.uuid4())
    actividad.qr_token = token
    actividad.qr_generated_at = datetime.utcnow()
    db.session.commit()
    registrar_notificacion(f"{current_user.username} generó código QR para la actividad '{actividad.title}'", 'success')
    return jsonify({'success': True, 'message': 'Código QR generado correctamente'})

@app.route('/admin/actividad/<int:id>/qr/imagen')
@login_required
@admin_required
def mostrar_qr_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    if not actividad.qr_token:
        flash("Esta actividad no tiene código QR generado aún.", "warning")
        return redirect(url_for('dashboard'))
    qr_buffer = generar_imagen_qr(actividad.qr_token)
    return Response(qr_buffer, mimetype='image/png')

@app.route('/admin/actividad/<int:id>/qr/pdf')
@login_required
@admin_required
def exportar_qr_pdf(id):
    actividad = Actividad.query.get_or_404(id)
    if not actividad.qr_token:
        token = str(uuid.uuid4())
        actividad.qr_token = token
        actividad.qr_generated_at = datetime.utcnow()
        db.session.commit()
    
    qr_buffer = generar_imagen_qr(actividad.qr_token)
    qr_image = Image(qr_buffer, width=5*cm, height=5*cm)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        alignment=1,
        fontSize=16,
        textColor=colors.HexColor('#008000'),
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        alignment=1,
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20
    )
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, leading=14)
    
    data = [
        ['Título:', actividad.title],
        ['Ponente:', actividad.speaker or 'No especificado'],
        ['Fecha:', actividad.date],
        ['Horario:', f"{actividad.start_time} - {actividad.end_time}"],
        ['Sede / Aula:', actividad.venue or 'No especificada'],
        ['Categoría:', actividad.category],
        ['Dirigido a:', actividad.career or 'Público general']
    ]
    table = Table(data, colWidths=[4*cm, 10*cm])
    table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0fdf4')),
    ]))
    
    story = []
    story.append(Paragraph("<b>UNIVERSIDAD DE EL SALVADOR</b>", title_style))
    story.append(Paragraph("UES San José del Rincón", subtitle_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"<b>{actividad.title}</b>", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Código de acceso para registrar asistencia:", normal_style))
    
    qr_table = Table([[qr_image]], colWidths=[14*cm])
    qr_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(qr_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("<i>Escanee este código QR para registrar su asistencia.</i>", normal_style))
    story.append(Paragraph("<i>Válido únicamente durante el horario de la actividad.</i>", normal_style))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Organiza: Unidad de Eventos Académicos", normal_style))
    story.append(Paragraph("UES San José del Rincón - Jornada Académica y Cultural", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return Response(buffer, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=QR_{actividad.title}.pdf'})

@app.route('/api/asistencia/registrar', methods=['POST'])
@login_required
def registrar_asistencia():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token no proporcionado'}), 400
    
    actividad = Actividad.query.filter_by(qr_token=token).first()
    if not actividad:
        return jsonify({'error': 'Código QR inválido'}), 404
    
    inscripcion = UserAgenda.query.filter_by(user_id=current_user.id, actividad_id=actividad.id).first()
    if not inscripcion:
        return jsonify({'error': 'No estás inscrito en esta actividad'}), 403
    
    ahora = datetime.now()
    fecha_hora_inicio = datetime.strptime(f"{actividad.date} {actividad.start_time}", '%Y-%m-%d %H:%M')
    fecha_hora_fin = datetime.strptime(f"{actividad.date} {actividad.end_time}", '%Y-%m-%d %H:%M') if actividad.end_time else None
    
    if ahora < fecha_hora_inicio:
        return jsonify({'error': 'La actividad aún no ha comenzado'}), 403
    if fecha_hora_fin and ahora > fecha_hora_fin:
        return jsonify({'error': 'La actividad ya ha terminado'}), 403
    
    ya_asistio = Asistencia.query.filter_by(user_id=current_user.id, actividad_id=actividad.id).first()
    if ya_asistio:
        return jsonify({'error': 'Ya registraste tu asistencia a esta actividad'}), 403
    
    nueva_asistencia = Asistencia(user_id=current_user.id, actividad_id=actividad.id)
    db.session.add(nueva_asistencia)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Asistencia registrada correctamente'})

@app.route('/admin/api/actividad/<int:id>/asistencias')
@login_required
@admin_required
def api_asistencias_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    asistencias = Asistencia.query.filter_by(actividad_id=id).all()
    return jsonify({
        'actividad_id': id,
        'titulo': actividad.title,
        'total': len(asistencias),
        'asistentes': [{
            'id': a.user.id,
            'student_id': a.user.student_id,
            'username': a.user.username,
            'email': a.user.email,
            'fecha_hora': a.fecha_hora_registro.strftime('%Y-%m-%d %H:%M:%S')
        } for a in asistencias]
    })

# =========================
# ENDPOINTS PARA NOTIFICACIONES (superadmin)
# =========================
@app.route('/admin/api/notificaciones')
@login_required
@superadmin_required
def api_notificaciones():
    notificaciones = Notificacion.query.order_by(Notificacion.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': n.id,
        'mensaje': n.mensaje,
        'tipo': n.tipo,
        'leida': n.leida,
        'timestamp': n.timestamp.isoformat()
    } for n in notificaciones])

@app.route('/admin/api/notificaciones/<int:id>/leer', methods=['POST'])
@login_required
@superadmin_required
def api_marcar_leida(id):
    notif = Notificacion.query.get_or_404(id)
    notif.leida = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/api/notificaciones/marcar_todas', methods=['POST'])
@login_required
@superadmin_required
def api_marcar_todas_leidas():
    Notificacion.query.update({Notificacion.leida: True})
    db.session.commit()
    return jsonify({'success': True})

# =========================
# UTILIDADES
# =========================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_roles_and_permissions():
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

    admin_email = app.config['MAIL_USERNAME']
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_roles_and_permissions()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )