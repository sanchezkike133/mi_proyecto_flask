from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from flask import Response, current_app
from datetime import datetime
import os
import hashlib

# ------------------------------
# Funciones para obtener logos únicos
# ------------------------------
def get_all_unique_logos(app=None):
    """
    Retorna una lista de rutas absolutas de todos los logos institucionales únicos
    (sin duplicados por contenido, comparando MD5).
    Si no se proporciona app, usa current_app.
    """
    if app is None:
        app = current_app
    from app.models.actividad import Actividad
    from app.extensions import db
    upload_folder = app.config['UPLOAD_FOLDER']
    logos_db = db.session.query(Actividad.logo_institucion).filter(Actividad.logo_institucion.isnot(None)).distinct().all()
    seen_hashes = set()
    unique_paths = []
    for (logo_filename,) in logos_db:
        if not logo_filename:
            continue
        full_path = os.path.join(upload_folder, logo_filename)
        if not os.path.exists(full_path):
            continue
        with open(full_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        if file_hash not in seen_hashes:
            seen_hashes.add(file_hash)
            unique_paths.append(full_path)
    return unique_paths

# ------------------------------
# Dibujar logos en el pie de página (canvas)
# ------------------------------
def draw_logos_footer(canvas_obj, doc, logos_paths, ancho_logo=1.5*cm, separacion=0.3*cm, margen_inferior=1.2*cm):
    """
    Dibuja los logos en el pie de página de cada hoja, centrados horizontalmente.
    - ancho_logo: ancho de cada logo en cm (alto automático proporcional)
    - separacion: espacio entre logos
    - margen_inferior: distancia desde el borde inferior de la página
    """
    if not logos_paths:
        return
    from reportlab.lib.utils import ImageReader
    num_logos = len(logos_paths)
    ancho_total = num_logos * ancho_logo + (num_logos - 1) * separacion
    pagina_ancho = doc.pagesize[0]
    inicio_x = (pagina_ancho - ancho_total) / 2.0
    y = margen_inferior

    for i, ruta in enumerate(logos_paths):
        if not os.path.exists(ruta):
            continue
        try:
            img = ImageReader(ruta)
            img_width, img_height = img.getSize()
            if img_width:
                proporcion = img_height / img_width
            else:
                proporcion = 1
            alto = ancho_logo * proporcion
            x = inicio_x + i * (ancho_logo + separacion)
            canvas_obj.drawImage(img, x, y, width=ancho_logo, height=alto, preserveAspectRatio=True, anchor='c')
        except:
            continue

# ------------------------------
# Generador principal de PDF
# ------------------------------
def generar_pdf_actividades(actividades, titulo_principal, subtitulo, columnas, mostrar_tipo_jornada=True, logos_unicos=None):
    """
    Genera un PDF con una tabla de actividades.
    Los logos se dibujan automáticamente en el pie de cada página.
    """
    if logos_unicos is None:
        logos_unicos = get_all_unique_logos()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.8*cm, bottomMargin=2.0*cm)  # Aumentado para dejar espacio a los logos
    story = []
    styles = getSampleStyleSheet()

    # Estilos
    estilo_titulo = ParagraphStyle(
        'TituloPrincipal', parent=styles['Heading1'], fontSize=18,
        textColor=colors.HexColor('#008000'), alignment=1, spaceAfter=6, fontName='Helvetica-Bold'
    )
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#333333'), alignment=1, spaceAfter=20
    )
    estilo_fecha = ParagraphStyle(
        'Fecha', parent=styles['Normal'], fontSize=9,
        textColor=colors.grey, alignment=2, spaceAfter=12
    )
    estilo_cabecera = ParagraphStyle(
        'CabeceraTabla', parent=styles['Normal'], fontSize=10,
        textColor=colors.white, alignment=1, fontName='Helvetica-Bold'
    )
    estilo_celda = ParagraphStyle(
        'CeldaTabla', parent=styles['Normal'], fontSize=9, leading=12
    )

    story.append(Paragraph(titulo_principal, estilo_titulo))
    story.append(Paragraph(subtitulo, estilo_subtitulo))
    story.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_fecha))
    story.append(Spacer(1, 0.3*cm))

    # Preparar columnas
    cols = columnas.copy()
    if mostrar_tipo_jornada:
        cols.insert(0, {'key': 'tipo', 'label': 'Tipo', 'width': 2.5*cm})

    total_width = sum(col['width'] for col in cols)
    page_width = landscape(A4)[0] - 3*cm
    if total_width < page_width:
        factor = page_width / total_width
        for col in cols:
            col['width'] = col['width'] * factor

    # Cabecera de tabla
    header_cells = [Paragraph(col['label'], estilo_cabecera) for col in cols]
    data_table = [header_cells]

    # Filas de datos
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

    # Crear tabla
    table = Table(data_table, colWidths=[col['width'] for col in cols], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#008000')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Documento generado automáticamente por el sistema de la Jornada Académica",
                          ParagraphStyle('Pie', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))

    # Funciones para dibujar el pie en todas las páginas
    def on_first_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        if logos_unicos:
            draw_logos_footer(canvas_obj, doc_obj, logos_unicos)
        canvas_obj.restoreState()

    def on_later_pages(canvas_obj, doc_obj):
        canvas_obj.saveState()
        if logos_unicos:
            draw_logos_footer(canvas_obj, doc_obj, logos_unicos)
        canvas_obj.restoreState()

    # Construir documento con los callbacks
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buffer.seek(0)
    return buffer

# ------------------------------
# Envío de PDF como respuesta HTTP
# ------------------------------
def send_pdf(buffer, filename):
    return Response(buffer, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename={filename}'})