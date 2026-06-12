# reactivar_admin.py
from app import app, db, User

with app.app_context():
    admin_email = 'sanchezkike133@gmail.com'
    user = User.query.filter_by(email=admin_email).first()
    if user:
        user.is_active = True
        db.session.commit()
        print(f"✅ Usuario {user.email} reactivado correctamente")
        print(f"   Rol: {user.role.name if user.role else 'sin rol'}")
        print(f"   Ahora puedes iniciar sesión")
    else:
        print(f"❌ No se encontró el usuario con email {admin_email}")
        print("   Revisa el email en la base de datos")