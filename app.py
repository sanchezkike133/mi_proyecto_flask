from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required
)

import os
from datetime import datetime

# =========================
# CREAR APP
# =========================

app = Flask(__name__)

# =========================
# CONFIGURACIÓN
# =========================

app.config['SECRET_KEY'] = 'clave_super_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =========================
# CONFIGURACIÓN DE UPLOADS
# =========================

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================
# BASE DE DATOS
# =========================

db = SQLAlchemy(app)

# =========================
# FLASK LOGIN
# =========================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = None

# =========================
# MODELO DE USUARIO
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))


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


# =========================
# USER LOADER
# =========================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =========================
# FUNCIÓN AUXILIAR
# =========================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# =========================
# RUTAS
# =========================

@app.route('/')
def index():
    return render_template('index.html')

# =========================
# REGISTRO
# =========================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        usuario_existente = User.query.filter_by(email=email).first()

        if usuario_existente:
            flash('El correo ya está registrado')
            return redirect(url_for('register'))

        nuevo_usuario = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario registrado correctamente')
        return redirect(url_for('login'))

    return render_template('register.html')

# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        usuario = User.query.filter_by(email=email).first()

        if usuario and usuario.password == password:
            login_user(usuario)
            flash('Inicio de sesión correcto')
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos')

    return render_template('login.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
@login_required
def logout():

    logout_user()
    flash('Sesión cerrada correctamente')
    return redirect(url_for('login'))

# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
@login_required
def dashboard():

    actividades = Actividad.query.all()
    return render_template('dashboard.html', actividades=actividades)

# =========================
# NUEVA ACTIVIDAD
# =========================

@app.route('/nueva_actividad', methods=['GET', 'POST'])
@login_required
def nueva_actividad():

    if request.method == 'POST':

        titulo = request.form['title']
        dia = request.form['day']
        categoria = request.form['category']
        fecha = request.form['date']
        hora_inicio = request.form['start_time']
        hora_fin = request.form.get('end_time', '')
        ponente = request.form.get('speaker', '')
        sede = request.form['venue']
        descripcion = request.form.get('description', '')

        imagen_filename = None

        if 'imagen' in request.files:

            file = request.files['imagen']

            if file and file.filename != '' and allowed_file(file.filename):

                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                imagen_filename = filename

        nueva = Actividad(
            title=titulo,
            day=dia,
            category=categoria,
            date=fecha,
            start_time=hora_inicio,
            end_time=hora_fin,
            speaker=ponente,
            venue=sede,
            description=descripcion,
            image=imagen_filename
        )

        db.session.add(nueva)
        db.session.commit()

        flash('Actividad registrada correctamente')
        return redirect(url_for('dashboard'))

    return render_template('nuevo.html')

# =========================
# DETALLE
# =========================

@app.route('/detalle/<int:id>')
@login_required
def detalle(id):

    actividad = Actividad.query.get_or_404(id)
    return render_template('detalle.html', actividad=actividad)

# =========================
# EDITAR
# =========================

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):

    actividad = Actividad.query.get_or_404(id)

    if request.method == 'POST':

        actividad.title = request.form['title']
        actividad.speaker = request.form.get('speaker', '')
        actividad.date = request.form['date']
        actividad.venue = request.form['venue']
        actividad.start_time = request.form['start_time']
        actividad.end_time = request.form.get('end_time', '')
        actividad.description = request.form.get('description', '')

        db.session.commit()

        flash('Actividad actualizada correctamente')
        return redirect(url_for('dashboard'))

    return render_template('editar.html', actividad=actividad)

# =========================
# ELIMINAR
# =========================

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):

    actividad = Actividad.query.get_or_404(id)

    if actividad.image:

        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], actividad.image)

        if os.path.exists(imagen_path):
            os.remove(imagen_path)

    db.session.delete(actividad)
    db.session.commit()

    flash('Actividad eliminada correctamente')
    return redirect(url_for('dashboard'))

# =========================
# ACTIVIDADES POR DÍA - ACTUALIZADAS ✅
# =========================

@app.route('/actividades/lunes')
def lunes():
    # Filtra actividades del día lunes
    actividades = Actividad.query.filter_by(day='Lunes').all()
    return render_template('actividades_lunes.html', actividades=actividades)

@app.route('/actividades/martes')
def martes():
    # Filtra actividades del día martes
    actividades = Actividad.query.filter_by(day='Martes').all()
    return render_template('actividades_martes.html', actividades=actividades)

@app.route('/actividades/miercoles')
def miercoles():
    # Filtra actividades del día miércoles
    actividades = Actividad.query.filter_by(day='Miércoles').all()
    return render_template('actividades_miercoles.html', actividades=actividades)

@app.route('/actividades/jueves')
def jueves():
    # Filtra actividades del día jueves
    actividades = Actividad.query.filter_by(day='Jueves').all()
    return render_template('actividades_jueves.html', actividades=actividades)

@app.route('/actividades/viernes')
def viernes():
    # Filtra actividades del día viernes
    actividades = Actividad.query.filter_by(day='Viernes').all()
    return render_template('actividades_viernes.html', actividades=actividades)

# =========================
# EJECUTAR APP
# =========================

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)