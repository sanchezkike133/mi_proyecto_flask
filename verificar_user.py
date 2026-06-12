from app import app, db, User

with app.app_context():
    # Buscar tu usuario específico
    usuario = User.query.filter_by(email="sanchezkike133@gmail.com").first()
    
    if usuario:
        print("✅ USUARIO ENCONTRADO:")
        print(f"   ID: {usuario.id}")
        print(f"   Email: {usuario.email}")
        print(f"   Password guardada: '{usuario.password}'")
        print(f"   Longitud password: {len(usuario.password)}")
    else:
        print("❌ USUARIO NO ENCONTRADO")
        
        # Mostrar todos los usuarios en la DB
        todos = User.query.all()
        print(f"\nUsuarios en la base de datos ({len(todos)}):")
        for u in todos:
            print(f"   - {u.email}")
            