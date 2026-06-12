from flask import current_app, render_template
from flask_mail import Message
from ..extensions import mail
from datetime import datetime

def send_email_code(email, code, student_name):
    school_name = "UES 'San José del Rincón'"
    year = datetime.now().year
    jornada = year - 2013
    event_name = f"{jornada}va Jornada Académica y Cultural {year}"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Verificación de registro</title>
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
            <div class="header"><h1>{school_name}</h1><p>{event_name}</p></div>
            <div class="content"><h2>Hola <strong>{student_name}</strong></h2>
            <p>Tu código de verificación para completar el registro es:</p>
            <div style="text-align: center;"><span class="code">{code}</span></div>
            <p>Válido por <strong>5 minutos</strong>.</p>
            <p>Si no solicitaste este registro, ignora este mensaje.</p></div>
            <div class="footer">&copy; {year} {school_name} - Todos los derechos reservados.</div>
        </div>
    </body>
    </html>
    """
    msg = Message(f"🔐 Código de verificación - {event_name}",
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.html = html_content
    msg.body = f"Hola {student_name},\n\nTu código de verificación es: {code}\n\nVálido por 5 minutos."
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error enviando correo: {e}")
        return False

def send_password_reset_code(email, code, student_name):
    school_name = "UES 'San José del Rincón'"
    year = datetime.now().year
    jornada = year - 2013
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Recuperación de contraseña</title>
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
            <div class="header"><h1>{school_name}</h1><p>{jornada}va Jornada Académica y Cultural {year}</p></div>
            <div class="content"><h2>Hola <strong>{student_name}</strong></h2>
            <p>Hemos recibido una solicitud para restablecer tu contraseña.</p>
            <p>Utiliza el siguiente código:</p>
            <div style="text-align: center;"><span class="code">{code}</span></div>
            <p>Válido por <strong>5 minutos</strong>.</p>
            <p>Si no solicitaste este cambio, ignora este mensaje.</p></div>
            <div class="footer">&copy; {year} {school_name} - Todos los derechos reservados.</div>
        </div>
    </body>
    </html>
    """
    msg = Message("🔐 Recuperación de contraseña - Jornada Académica",
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.html = html_content
    msg.body = f"Hola {student_name},\n\nTu código de recuperación es: {code}\n\nVálido por 5 minutos."
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error enviando correo de recuperación: {e}")
        return False