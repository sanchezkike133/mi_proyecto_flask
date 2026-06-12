from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, Role, MatriculaValida, VerificationCode, PasswordReset
from ..extensions import db
from ..services.email_service import send_email_code, send_password_reset_code
import uuid
import random
from datetime import datetime, timedelta

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('public.ver_actividades'))
        else:
            flash("Credenciales incorrectas o cuenta inactiva.", "error")
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    if current_user.is_authenticated:
        current_user.session_token = str(uuid.uuid4())
        db.session.commit()
    logout_user()
    session.clear()
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET'])
def register_form():
    if current_user.is_authenticated:
        return redirect(url_for('public.ver_actividades'))
    return render_template('register.html')

@bp.route('/register/send-code', methods=['POST'])
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

@bp.route('/register/verify', methods=['POST'])
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

@bp.route('/forgot-password', methods=['GET', 'POST'])
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
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            from flask_mail import Message
            from ..extensions import mail
            msg = Message("Recuperación de contraseña - Administrador",
                          sender=current_app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Hola,\n\nHaz clic para restablecer tu contraseña: {reset_link}\n\nVálido por 15 minutos."
            try:
                mail.send(msg)
                flash("Correo enviado.", "success")
            except Exception as e:
                flash("Error al enviar correo.", "error")
        else:
            flash("El correo no corresponde a un administrador.", "error")
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset = PasswordReset.query.filter_by(token=token).first()
    if not reset or reset.expires_at < datetime.utcnow():
        flash("Token inválido o expirado.", "error")
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form.get('confirm_password')
        if not password or password != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for('auth.reset_password', token=token))
        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return redirect(url_for('auth.reset_password', token=token))
        user = User.query.filter_by(email=reset.email).first()
        if user:
            user.set_password(password)
            db.session.commit()
        db.session.delete(reset)
        db.session.commit()
        flash("Contraseña actualizada. Inicia sesión.", "success")
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html')

@bp.route('/forgot-password-student', methods=['GET', 'POST'])
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
                return redirect(url_for('auth.reset_password_student'))
            else:
                flash("Error al enviar el código.", "error")
        else:
            flash("No se encontró una cuenta de estudiante con esos datos.", "error")
        return redirect(url_for('auth.login'))
    return render_template('forgot_password_student.html')

@bp.route('/reset-password-student', methods=['GET', 'POST'])
def reset_password_student():
    if request.method == 'POST':
        code = request.form.get('code')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        email = session.get('reset_email')
        if not email:
            flash("No hay solicitud de recuperación activa.", "error")
            return redirect(url_for('auth.forgot_password_student'))
        if not code or not password or not confirm:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for('auth.reset_password_student'))
        if password != confirm:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for('auth.reset_password_student'))
        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
            return redirect(url_for('auth.reset_password_student'))
        record = VerificationCode.query.filter_by(phone=email, code=code, used=False).first()
        if not record or record.expires_at < datetime.utcnow():
            flash("Código inválido o expirado.", "error")
            return redirect(url_for('auth.reset_password_student'))
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            record.used = True
            db.session.commit()
            session.pop('reset_email', None)
            flash("Contraseña actualizada. Inicia sesión.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Usuario no encontrado.", "error")
            return redirect(url_for('auth.forgot_password_student'))
    if not session.get('reset_email'):
        flash("No hay una solicitud de recuperación activa.", "warning")
        return redirect(url_for('auth.forgot_password_student'))
    return render_template('reset_password_code.html')