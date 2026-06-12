from app import app, db
from app import User, Actividad, ActividadGuardada, PasswordReset

with app.app_context():
    print("\n" + "="*60)
    print("📊 CONTENIDO DE LA BASE DE DATOS")
    print("="*60)
    
    # 1. Ver usuarios
    print("\n👥 TABLA: user")
    print("-" * 40)
    usuarios = User.query.all()
    if usuarios:
        for u in usuarios:
            print(f"ID: {u.id} | Username: {u.username} | Email: {u.email}")
            print(f"   Password Hash: {u.password_hash[:50]}..." if u.password_hash else "   Sin contraseña")
    else:
        print("   (vacía)")
    
    # 2. Ver actividades
    print("\n📅 TABLA: actividad")
    print("-" * 40)
    actividades = Actividad.query.all()
    if actividades:
        for a in actividades:
            print(f"ID: {a.id} | Título: {a.title} | Día: {a.day} | Hora: {a.start_time}")
    else:
        print("   (vacía)")
    
    # 3. Ver actividades guardadas
    print("\n⭐ TABLA: actividad_guardada")
    print("-" * 40)
    guardadas = ActividadGuardada.query.all()
    if guardadas:
        for g in guardadas:
            print(f"ID: {g.id} | Usuario ID: {g.user_id} | Actividad ID: {g.actividad_id} | Fecha: {g.fecha_guardado}")
    else:
        print("   (vacía)")
    
    # 4. Ver recuperaciones de contraseña
    print("\n🔐 TABLA: password_reset")
    print("-" * 40)
    resets = PasswordReset.query.all()
    if resets:
        for r in resets:
            print(f"ID: {r.id} | Email: {r.email} | Token: {r.token[:30]}... | Expira: {r.expires_at}")
    else:
        print("   (vacía)")
    
    print("\n" + "="*60)
    print("✅ Consulta completada")
    print("="*60)