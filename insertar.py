# agregar_ponencias_hoy.py
import sys
import os
from datetime import datetime, timedelta
from app import app, db, Actividad  # Importa tu app y modelos
from werkzeug.security import generate_password_hash

# Configurar el contexto de la aplicación
with app.app_context():
    # Obtener la fecha actual (YYYY-MM-DD)
    hoy = datetime.now().date()
    fecha_str = hoy.isoformat()
    año_actual = hoy.year
    jornada_num = año_actual - 2013  # Para referencia, pero como hoy no es diciembre, será tipo 'extra'

    # Datos de las ponencias (título, ponente, hora inicio, hora fin, sede, categoría, dirigido a)
    # Duración de 1 hora por ponencia (60 minutos)
    ponencias = [
        {"hora": "10:00", "titulo": "Inteligencia Artificial en la Educación", "ponente": "Dra. María González", "sede": "Aula Magna", "categoria": "Conferencias académicas", "dirigido": "Público en general"},
        {"hora": "11:00", "titulo": "Desarrollo de Software con IA Generativa", "ponente": "Ing. Carlos Méndez", "sede": "Salón de Conferencias", "categoria": "Conferencias académicas", "dirigido": "Ingeniería en Sistemas Computacionales"},
        {"hora": "12:00", "titulo": "Innovación Agrícola Sostenible", "ponente": "Dr. Juan Pérez", "sede": "Plazoleta Institucional", "categoria": "Conferencias académicas", "dirigido": "Ingeniería en Innovación Agrícola Sustentable"},
        {"hora": "13:00", "titulo": "Estrategias de Contaduría Digital", "ponente": "Mtra. Laura Fernández", "sede": "Sala de Cómputo", "categoria": "Talleres prácticos", "dirigido": "Licenciatura en Contaduría"},
        {"hora": "14:00", "titulo": "Networking Profesional en el Ámbito Universitario", "ponente": "Lic. Roberto Sánchez", "sede": "Aula Magna", "categoria": "Actividades de vinculación y networking", "dirigido": "Público en general"},
        {"hora": "15:00", "titulo": "Panel: El Futuro del Trabajo", "ponente": "Dra. Ana Martínez", "sede": "Salón de Conferencias", "categoria": "Mesas redondas y paneles de discusión", "dirigido": "Todas las carreras"},
        {"hora": "16:00", "titulo": "Exposición de Proyectos Estudiantiles", "ponente": "Comité Organizador", "sede": "Plazoleta Institucional", "categoria": "Exposiciones y muestras de proyectos", "dirigido": "Público en general"},
        {"hora": "17:00", "titulo": "Clausura y Entrega de Reconocimientos", "ponente": "Rectoría", "sede": "Aula Magna", "categoria": "Término", "dirigido": "Todos los asistentes"},
    ]

    # Mapeo de días de la semana (para calcular day a partir de la fecha)
    dias_semana = {
        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
    }
    dia_semana = dias_semana[hoy.weekday()]

    # Insertar cada ponencia
    contador = 0
    for p in ponencias:
        hora_inicio = p["hora"]
        # Calcular hora fin = hora_inicio + 1 hora
        hora_obj = datetime.strptime(hora_inicio, "%H:%M")
        hora_fin_obj = hora_obj + timedelta(minutes=60)
        hora_fin = hora_fin_obj.strftime("%H:%M")

        # Verificar si ya existe una actividad en la misma fecha, misma sede y horario solapado
        conflictos = Actividad.query.filter(
            Actividad.date == fecha_str,
            Actividad.venue == p["sede"],
            Actividad.start_time < hora_fin,
            Actividad.end_time > hora_inicio
        ).first()
        if conflictos:
            print(f"⚠️ Conflicto de horario para '{p['titulo']}' en {p['sede']} de {hora_inicio} a {hora_fin}. Se omite.")
            continue

        # Determinar event_type (jornada solo si mes es diciembre)
        event_type = 'extra'  # Por defecto extracurricular
        jornada_numero = None
        if hoy.month == 12:  # Si hoy es diciembre, se considera jornada
            event_type = 'jornada'
            jornada_numero = jornada_num

        nueva_actividad = Actividad(
            title=p["titulo"],
            day=dia_semana,
            category=p["categoria"],
            date=fecha_str,
            start_time=hora_inicio,
            end_time=hora_fin,
            speaker=p["ponente"],
            venue=p["sede"],
            description=f"{p['titulo']} - Ponencia impartida por {p['ponente']}. Actividad académica de la jornada.",
            career=p["dirigido"],
            institution="UES San José del Rincón",
            speaker_email="eventos@ues.edu.sv",
            speaker_phone="",
            academic_degree="",
            specialty="",
            experience="",
            social="",
            bio="",
            event_type=event_type,
            jornada_numero=jornada_numero,
            qr_token=None,
            qr_generated_at=None
        )
        db.session.add(nueva_actividad)
        contador += 1
        print(f"✅ Agregada: {p['titulo']} - {hora_inicio} a {hora_fin} en {p['sede']}")

    db.session.commit()
    print(f"\n🎉 Se agregaron {contador} actividades para el día {fecha_str} ({dia_semana}).")

    # Mostrar resumen
    print("\n📋 Lista de actividades agregadas:")
    for p in ponencias:
        print(f"   - {p['hora']}: {p['titulo']} - {p['ponente']} ({p['sede']})")