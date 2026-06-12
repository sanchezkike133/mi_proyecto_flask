from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, current_app
from flask_login import login_required, current_user
from ..models import Actividad, ActivityLog, Asistencia, UserAgenda, Notificacion, User
from ..extensions import db
from ..services.validators import validar_horario_actividad
from ..services.qr_service import generar_imagen_qr
from ..services.pdf_service import generar_pdf_actividades, send_pdf, get_all_unique_logos, draw_logos_footer
from ..decorators import admin_required, permission_required, no_cache
import os
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from io import BytesIO
from sqlalchemy import func

bp = Blueprint('admin', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def registrar_notificacion(mensaje, tipo='info', usuario_id=None):
    notif = Notificacion(mensaje=mensaje, tipo=tipo, usuario_id=usuario_id)
    db.session.add(notif)
    db.session.commit()

@bp.route('/dashboard')
@login_required
@permission_required('view_dashboard')
@no_cache
def dashboard():
    actividades = Actividad.query.all()
    usuarios_count = User.query.count()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(20).all()
    return render_template('dashboard.html', actividades=actividades, usuarios_count=usuarios_count, logs=logs)

@bp.route('/api/stats')
@login_required
@admin_required
def admin_api_stats():
    total_actividades = Actividad.query.count()
    total_jornada = Actividad.query.filter_by(event_type='jornada').count()
    total_extra = Actividad.query.filter_by(event_type='extra').count()
    total_usuarios = User.query.count()
    actividad_mas_interes = db.session.query(
        UserAgenda.actividad_id, func.count(UserAgenda.actividad_id).label('count')
    ).group_by(UserAgenda.actividad_id).order_by(func.count(UserAgenda.actividad_id).desc()).first()
    top_actividad = None
    if actividad_mas_interes:
        act = Actividad.query.get(actividad_mas_interes.actividad_id)
        if act:
            top_actividad = {'id': act.id, 'title': act.title, 'total': actividad_mas_interes.count}
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

@bp.route('/nueva_actividad', methods=['GET', 'POST'])
@login_required
@admin_required
@no_cache
def nueva_actividad():
    if request.method == 'POST':
        required_fields = ['title', 'day', 'category', 'date', 'start_time', 'speaker', 'venue']
        for field in required_fields:
            if not request.form.get(field):
                flash(f"El campo {field} es obligatorio.", "error")
                return redirect(url_for('admin.nueva_actividad'))
        fecha = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form.get('end_time')
        venue = request.form['venue']
        if not end_time:
            flash("Debe especificar una hora de fin.", "error")
            return redirect(url_for('admin.nueva_actividad'))
        valido, msg = validar_horario_actividad(fecha, start_time, end_time, venue)
        if not valido:
            flash(msg, "error")
            return redirect(url_for('admin.nueva_actividad'))
        
        # Asegurar que la carpeta de uploads existe
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Imagen del ponente
        file = request.files.get('imagen')
        image_filename = None
        if file and allowed_file(file.filename):
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            file.save(os.path.join(upload_folder, filename))
            image_filename = filename
        
        # Logo institucional
        file_logo = request.files.get('logo_institucion')
        logo_filename = None
        if file_logo and allowed_file(file_logo.filename):
            from werkzeug.utils import secure_filename
            logo_filename = secure_filename(file_logo.filename)
            logo_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + logo_filename
            file_logo.save(os.path.join(upload_folder, logo_filename))
        
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
            jornada_numero=jornada_numero,
            logo_institucion=logo_filename
        )
        db.session.add(nueva)
        db.session.commit()
        log = ActivityLog(user_id=current_user.id, action='crear', actividad_id=nueva.id)
        db.session.add(log)
        db.session.commit()
        registrar_notificacion(f"{current_user.username} creó la actividad '{nueva.title}'", 'success')
        flash("Actividad creada correctamente", "success")
        return redirect(url_for('admin.dashboard'))
    return render_template('nuevo.html')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
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
                return redirect(url_for('admin.editar', id=id))
        fecha = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form.get('end_time')
        venue = request.form['venue']
        if not end_time:
            flash("Debe especificar una hora de fin.", "error")
            return redirect(url_for('admin.editar', id=id))
        valido, msg = validar_horario_actividad(fecha, start_time, end_time, venue, actividad_id=id)
        if not valido:
            flash(msg, "error")
            return redirect(url_for('admin.editar', id=id))
        
        # Asegurar que la carpeta de uploads existe
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
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
        
        # Imagen del ponente
        file = request.files.get('imagen')
        if file and allowed_file(file.filename):
            if actividad.image:
                old_path = os.path.join(upload_folder, actividad.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + filename
            file.save(os.path.join(upload_folder, filename))
            actividad.image = filename
        
        # Logo institucional
        file_logo = request.files.get('logo_institucion')
        if file_logo and allowed_file(file_logo.filename):
            if actividad.logo_institucion:
                old_logo_path = os.path.join(upload_folder, actividad.logo_institucion)
                if os.path.exists(old_logo_path):
                    os.remove(old_logo_path)
            from werkzeug.utils import secure_filename
            logo_filename = secure_filename(file_logo.filename)
            logo_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + logo_filename
            file_logo.save(os.path.join(upload_folder, logo_filename))
            actividad.logo_institucion = logo_filename
        
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
        return redirect(url_for('admin.dashboard'))
    return render_template('editar.html', actividad=actividad)

@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
@no_cache
def eliminar(id):
    actividad = Actividad.query.get_or_404(id)
    titulo = actividad.title
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if actividad.image:
        path = os.path.join(upload_folder, actividad.image)
        if os.path.exists(path):
            os.remove(path)
    if actividad.logo_institucion:
        logo_path = os.path.join(upload_folder, actividad.logo_institucion)
        if os.path.exists(logo_path):
            os.remove(logo_path)
    db.session.delete(actividad)
    db.session.commit()
    log = ActivityLog(user_id=current_user.id, action='eliminar', actividad_id=id)
    db.session.add(log)
    db.session.commit()
    registrar_notificacion(f"{current_user.username} eliminó la actividad '{titulo}'", 'danger')
    flash("Actividad eliminada correctamente", "warning")
    return redirect(url_for('admin.dashboard'))

@bp.route('/exportar/jornada')
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
    logos = get_all_unique_logos(current_app)
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=titulo,
        subtitulo="Universidad Mexiquense del Bicentenario - Campus San José del Rincón",
        columnas=columnas,
        mostrar_tipo_jornada=False,
        logos_unicos=logos
    )
    return send_pdf(pdf_buffer, f'jornada_{dia}.pdf')

@bp.route('/exportar/generales')
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
    from sqlalchemy import or_
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
    logos = get_all_unique_logos(current_app)
    pdf_buffer = generar_pdf_actividades(
        actividades_filtradas,
        titulo_principal=titulo,
        subtitulo="Universidad Mexiquense del Bicentenario - Campus San José del Rincón",
        columnas=columnas,
        mostrar_tipo_jornada=True,
        logos_unicos=logos
    )
    return send_pdf(pdf_buffer, 'eventos_generales.pdf')

@bp.route('/exportar/generales/fecha/<fecha>')
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
    logos = get_all_unique_logos(current_app)
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=f"Eventos Generales - {fecha}",
        subtitulo="Universidad Mexiquense del Bicentenario - Campus San José del Rincón",
        columnas=columnas,
        mostrar_tipo_jornada=True,
        logos_unicos=logos
    )
    return send_pdf(pdf_buffer, f'eventos_{fecha}.pdf')

@bp.route('/exportar/generales/rango/<desde>/<hasta>')
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
    logos = get_all_unique_logos(current_app)
    pdf_buffer = generar_pdf_actividades(
        actividades,
        titulo_principal=f"Eventos Generales del {desde} al {hasta}",
        subtitulo="Universidad Mexiquense del Bicentenario - Campus San José del Rincón",
        columnas=columnas,
        mostrar_tipo_jornada=True,
        logos_unicos=logos
    )
    return send_pdf(pdf_buffer, f'eventos_{desde}_a_{hasta}.pdf')

@bp.route('/actividad/<int:id>/qr/generar', methods=['POST'])
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

@bp.route('/actividad/<int:id>/qr/imagen')
@login_required
@admin_required
def mostrar_qr_actividad(id):
    actividad = Actividad.query.get_or_404(id)
    if not actividad.qr_token:
        flash("Esta actividad no tiene código QR generado aún.", "warning")
        return redirect(url_for('admin.dashboard'))
    qr_buffer = generar_imagen_qr(actividad.qr_token)
    return Response(qr_buffer, mimetype='image/png')

@bp.route('/actividad/<int:id>/qr/pdf')
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2.2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=16, textColor=colors.HexColor('#008000'), spaceAfter=10)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], alignment=1, fontSize=12, textColor=colors.grey, spaceAfter=20)
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
    story.append(Paragraph("<b>UNIVERSIDAD MEXIQUENSE DEL BICENTENARIO</b>", title_style))
    story.append(Paragraph("Campus San José del Rincón", subtitle_style))
    story.append(Spacer(1, 0.5*cm))
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
    story.append(Paragraph("Universidad Mexiquense del Bicentenario - Campus San José del Rincón", normal_style))

    # ========== OBTENER TODOS LOS LOGOS ÚNICOS DEL SISTEMA ==========
    logos_globales = get_all_unique_logos(current_app)

    # Funciones para dibujar el pie de página en cada hoja
    def on_first_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        if logos_globales:
            draw_logos_footer(canvas_obj, doc_obj, logos_globales, ancho_logo=1.5*cm, separacion=0.3*cm, margen_inferior=1.2*cm)
        canvas_obj.restoreState()

    def on_later_pages(canvas_obj, doc_obj):
        canvas_obj.saveState()
        if logos_globales:
            draw_logos_footer(canvas_obj, doc_obj, logos_globales, ancho_logo=1.5*cm, separacion=0.3*cm, margen_inferior=1.2*cm)
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buffer.seek(0)
    return Response(buffer, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=QR_{actividad.title}.pdf'})

@bp.route('/api/actividad/<int:id>/asistencias')
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

@bp.route('/api/actividad/<int:id>/interesados')
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