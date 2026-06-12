# seed_matriculas.py
from app import app, db, MatriculaValida

# Generar todas las matrículas desde 13220001 hasta 13250100
matriculas = []

# Rangos: 1322, 1323, 1324, 1325 con 100 números cada uno (01 a 100)
for prefijo in [1322, 1323, 1324, 1325]:
    for i in range(1, 101):
        matriculas.append(f"{prefijo}{i:04d}")

print(f"Total de matrículas a insertar: {len(matriculas)}")

with app.app_context():
    db.create_all()  # asegura que la tabla exista
    count = 0
    for mat in matriculas:
        if not MatriculaValida.query.filter_by(student_id=mat).first():
            db.session.add(MatriculaValida(student_id=mat))
            count += 1
    db.session.commit()
    print(f"Se insertaron {count} matrículas nuevas. Total en tabla: {MatriculaValida.query.count()}")