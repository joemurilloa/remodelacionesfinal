from app import app, db
from models import Cliente, Cotizacion, ItemCotizacion, Factura, ItemFactura, CuentaBancaria, CategoriaTransaccion, Transaccion
import os

# Asegurarse de que la carpeta instance existe
os.makedirs('instance', exist_ok=True)

def init_db():
    with app.app_context():
        # Eliminar todas las tablas existentes
        db.drop_all()
        
        # Crear todas las tablas
        db.create_all()
        
        print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db() 