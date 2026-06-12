from datetime import datetime
from ..models import Actividad
from ..extensions import db

def validar_horario_actividad(fecha, start_time, end_time, venue, actividad_id=None):
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