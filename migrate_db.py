import sqlite3
import os
from datetime import datetime

def migrate_database():
    # Ruta a la base de datos
    db_path = 'sistema_cotizaciones.db'
    
    # Verificar si la base de datos existe
    if not os.path.exists(db_path):
        print("La base de datos no existe. No se puede realizar la migración.")
        return
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna numero_factura ya existe
        cursor.execute("PRAGMA table_info(factura)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'numero_factura' not in columns:
            print("Añadiendo columna numero_factura a la tabla factura...")
            
            # Crear una tabla temporal con la nueva estructura
            cursor.execute("""
                CREATE TABLE factura_temp (
                    id INTEGER PRIMARY KEY,
                    numero_factura TEXT NOT NULL UNIQUE,
                    cliente_id INTEGER NOT NULL,
                    cotizacion_id INTEGER,
                    fecha DATETIME,
                    fecha_vencimiento DATETIME,
                    descripcion TEXT,
                    pagada BOOLEAN,
                    fecha_pago DATETIME,
                    FOREIGN KEY (cliente_id) REFERENCES cliente (id),
                    FOREIGN KEY (cotizacion_id) REFERENCES cotizacion (id)
                )
            """)
            
            # Obtener todas las facturas existentes
            cursor.execute("SELECT id, cliente_id, cotizacion_id, fecha, fecha_vencimiento, descripcion, pagada, fecha_pago FROM factura")
            facturas = cursor.fetchall()
            
            # Insertar las facturas en la tabla temporal con números únicos
            for factura in facturas:
                factura_id, cliente_id, cotizacion_id, fecha, fecha_vencimiento, descripcion, pagada, fecha_pago = factura
                
                # Generar número de factura único
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S.%f')
                prefijo = f"INV-{fecha_obj.strftime('%Y%m%d')}-{str(factura_id).zfill(4)}"
                
                # Insertar en la tabla temporal
                cursor.execute("""
                    INSERT INTO factura_temp 
                    (id, numero_factura, cliente_id, cotizacion_id, fecha, fecha_vencimiento, descripcion, pagada, fecha_pago)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (factura_id, prefijo, cliente_id, cotizacion_id, fecha, fecha_vencimiento, descripcion, pagada, fecha_pago))
            
            # Eliminar la tabla original y renombrar la temporal
            cursor.execute("DROP TABLE factura")
            cursor.execute("ALTER TABLE factura_temp RENAME TO factura")
            
            print("Migración completada con éxito.")
        else:
            print("La columna numero_factura ya existe en la tabla factura.")
        
        # Confirmar los cambios
        conn.commit()
        
    except Exception as e:
        print(f"Error durante la migración: {str(e)}")
        conn.rollback()
    
    finally:
        # Cerrar la conexión
        conn.close()

if __name__ == "__main__":
    migrate_database() 