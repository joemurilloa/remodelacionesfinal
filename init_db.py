from app import app, db
import os

# Asegurarse de que la carpeta instance existe
os.makedirs('instance', exist_ok=True)

with app.app_context():
    print("Eliminando todas las tablas existentes...")
    db.drop_all()
    
    print("Creando todas las tablas...")
    db.create_all()
    
    # Verificar que la tabla factura existe y tiene la columna numero_factura
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('factura')]
    print(f"Columnas en la tabla factura: {columns}")
    
    print("Base de datos inicializada correctamente.") 