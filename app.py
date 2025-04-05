from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from models import db, Cliente, Cotizacion, Factura, ItemCotizacion, ItemFactura, CuentaBancaria, CategoriaTransaccion, Transaccion
import pdf_generator
import backup_drive
import logging
from werkzeug.utils import secure_filename
import glob
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_para_desarrollo'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema_cotizaciones.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'pdfs')

# Asegurar que exista la carpeta para PDFs
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializar la base de datos
db.init_app(app)

# Crear todas las tablas si no existen
with app.app_context():
    db.create_all()

# Rutas para la página principal
@app.route('/')
def home():
    return render_template('home.html')

# Rutas para clientes
@app.route('/clientes')
def listar_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes/listar.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        rut = request.form['rut']
        
        nuevo_cliente = Cliente(nombre=nombre, email=email, telefono=telefono, 
                              direccion=direccion, rut=rut)
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('Cliente agregado correctamente')
        
        # Exportar solo el nuevo cliente a Google Sheets
        try:
            exito, mensaje = backup_drive.exportar_clientes_a_sheets(cliente_nuevo=nuevo_cliente)
            if not exito:
                logging.error(f"Error al exportar cliente a Google Sheets: {mensaje}")
        except Exception as e:
            logging.error(f"Error al exportar cliente a Google Sheets: {str(e)}")
        
        return redirect(url_for('listar_clientes'))
    
    return render_template('clientes/nuevo.html')

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'POST':
        cliente.nombre = request.form['nombre']
        cliente.email = request.form['email']
        cliente.telefono = request.form['telefono']
        cliente.direccion = request.form['direccion']
        cliente.rut = request.form['rut']
        
        db.session.commit()
        flash('Cliente actualizado correctamente')
        
        # Exportar solo el cliente editado a Google Sheets
        try:
            exito, mensaje = backup_drive.exportar_clientes_a_sheets(cliente_nuevo=cliente)
            if not exito:
                logging.error(f"Error al exportar cliente a Google Sheets: {mensaje}")
        except Exception as e:
            logging.error(f"Error al exportar cliente a Google Sheets: {str(e)}")
        
        return redirect(url_for('listar_clientes'))
    
    return render_template('clientes/editar.html', cliente=cliente)


@app.route('/clientes/eliminar/<int:id>')
def eliminar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente eliminado correctamente')
    return redirect(url_for('listar_clientes'))

# Rutas para cotizaciones
@app.route('/cotizaciones')
def listar_cotizaciones():
    cotizaciones = Cotizacion.query.all()
    return render_template('cotizaciones/listar.html', cotizaciones=cotizaciones)

@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
def nueva_cotizacion():
    clientes = Cliente.query.all()
    now = datetime.now()
    
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        validez = int(request.form['validez'])
        descripcion = request.form['descripcion']
        
        nueva_cotizacion = Cotizacion(
            cliente_id=cliente_id,
            fecha=fecha,
            validez=validez,
            descripcion=descripcion
        )
        
        db.session.add(nueva_cotizacion)
        db.session.commit()
        
        # Procesar items
        nombres = request.form.getlist('item_nombre[]')
        cantidades = request.form.getlist('item_cantidad[]')
        precios = request.form.getlist('item_precio[]')
        
        for i in range(len(nombres)):
            if nombres[i]:  # Solo procesar si hay un nombre
                item = ItemCotizacion(
                    cotizacion_id=nueva_cotizacion.id,
                    nombre=nombres[i],
                    cantidad=int(cantidades[i]),
                    precio_unitario=float(precios[i])
                )
                db.session.add(item)
        
        db.session.commit()
        
        # Generar PDF
        pdf_filename = pdf_generator.generar_pdf_cotizacion(nueva_cotizacion)
        
        flash('Cotización creada correctamente')
        return redirect(url_for('ver_cotizacion', id=nueva_cotizacion.id))
    
    return render_template('cotizaciones/nueva_cotizacion.html', clientes=clientes, now=now)


@app.route('/cotizaciones/ver/<int:id>')
def ver_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)
    
    # Buscar el PDF más reciente para esta cotización
    pdf_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    pdf_pattern = f"cotizacion_{id}_*.pdf"
    pdf_files = glob.glob(os.path.join(pdf_dir, pdf_pattern))
    
    if pdf_files:
        # Usar el PDF más reciente
        pdf_filename = os.path.basename(max(pdf_files, key=os.path.getctime))
    else:
        # Si no existe, generarlo
        pdf_filename = pdf_generator.generar_pdf_cotizacion(cotizacion)
    
    return render_template('cotizaciones/ver.html', cotizacion=cotizacion, pdf_filename=pdf_filename)

@app.route('/cotizaciones/pdf/<int:id>')
def pdf_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)
    
    # Buscar el PDF más reciente para esta cotización
    pdf_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    pdf_pattern = f"cotizacion_{id}_*.pdf"
    pdf_files = glob.glob(os.path.join(pdf_dir, pdf_pattern))
    
    if pdf_files:
        # Usar el PDF más reciente
        pdf_filename = os.path.basename(max(pdf_files, key=os.path.getctime))
    else:
        # Si no existe, generarlo
        pdf_filename = pdf_generator.generar_pdf_cotizacion(cotizacion)
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename)

@app.route('/cotizaciones/a-factura/<int:id>')
def cotizacion_a_factura(id):
    cotizacion = Cotizacion.query.get_or_404(id)
    
    # Generar número de factura único
    # Formato: INV-YYYYMMDD-XXXX (donde XXXX es un número secuencial)
    fecha_actual = datetime.now()
    prefijo = f"INV-{fecha_actual.strftime('%Y%m%d')}-"
    
    # Buscar la última factura con este prefijo
    ultima_factura = Factura.query.filter(Factura.numero_factura.like(f"{prefijo}%")).order_by(Factura.numero_factura.desc()).first()
    
    if ultima_factura:
        # Extraer el número secuencial y aumentarlo en 1
        ultimo_numero = int(ultima_factura.numero_factura.split('-')[-1])
        nuevo_numero = f"{prefijo}{str(ultimo_numero + 1).zfill(4)}"
    else:
        # Si no hay facturas con este prefijo, empezar con 0001
        nuevo_numero = f"{prefijo}0001"
    
    # Crear nueva factura basada en la cotización
    nueva_factura = Factura(
        numero_factura=nuevo_numero,
        cliente_id=cotizacion.cliente_id,
        cotizacion_id=cotizacion.id,
        fecha=datetime.now()
    )
    
    db.session.add(nueva_factura)
    db.session.commit()
    
    # Copiar items de la cotización a la factura
    for item_cotizacion in cotizacion.items:
        item_factura = ItemFactura(
            factura_id=nueva_factura.id,
            nombre=item_cotizacion.nombre,
            cantidad=item_cotizacion.cantidad,
            precio_unitario=item_cotizacion.precio_unitario
        )
        db.session.add(item_factura)
    
    db.session.commit()
    
    # Generar PDF de la factura
    pdf_generator.generar_pdf_factura(nueva_factura)
    
    flash('Cotización convertida a factura correctamente')
    return redirect(url_for('ver_factura', id=nueva_factura.id))

# Rutas para facturas
@app.route('/facturas')
def listar_facturas():
    facturas = Factura.query.all()
    return render_template('facturas/listar.html', facturas=facturas)

@app.route('/facturas/ver/<int:id>')
def ver_factura(id):
    factura = Factura.query.get_or_404(id)
    
    # Buscar el PDF más reciente para esta factura
    pdf_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    pdf_pattern = f"factura_{id}_*.pdf"
    pdf_files = glob.glob(os.path.join(pdf_dir, pdf_pattern))
    
    if pdf_files:
        # Usar el PDF más reciente
        pdf_filename = os.path.basename(max(pdf_files, key=os.path.getctime))
    else:
        # Si no existe, generarlo
        pdf_filename = pdf_generator.generar_pdf_factura(factura)
    
    return render_template('facturas/ver.html', factura=factura, pdf_filename=pdf_filename)

@app.route('/facturas/pdf/<int:id>')
def pdf_factura(id):
    factura = Factura.query.get_or_404(id)
    
    # Buscar el PDF más reciente para esta factura
    pdf_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    pdf_pattern = f"factura_{id}_*.pdf"
    pdf_files = glob.glob(os.path.join(pdf_dir, pdf_pattern))
    
    if pdf_files:
        # Usar el PDF más reciente
        pdf_filename = os.path.basename(max(pdf_files, key=os.path.getctime))
    else:
        # Si no existe, generarlo
        pdf_filename = pdf_generator.generar_pdf_factura(factura)
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename)

# Añadida la función marcar_factura_pagada que faltaba
@app.route('/facturas/marcar-pagada/<int:id>', methods=['POST'])
def marcar_factura_pagada(id):
    try:
        factura = Factura.query.get_or_404(id)
        factura.pagada = True
        factura.fecha_pago = datetime.now()
        db.session.commit()
        
        # Regenerar el PDF con el nuevo estado de pago
        pdf_generator.generar_pdf_factura(factura)
        
        flash('Factura marcada como pagada correctamente')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al marcar factura como pagada: {str(e)}')
    return redirect(url_for('ver_factura', id=id))

# Ruta para iniciar backup manual
@app.route('/backup')
def realizar_backup():
    try:
        # Utilizamos la nueva función de backup completo
        exito, mensaje = backup_drive.realizar_backup_completo()
        if exito:
            flash(f'Backup realizado correctamente: {mensaje}')
        else:
            flash(f'Error al realizar backup: {mensaje}')
    except Exception as e:
        flash(f'Error al realizar el backup: {str(e)}')
    return redirect(url_for('home'))

@app.route('/saludz')
def health_check():
    return "OK", 200

# Rutas para el módulo de cashflow
@app.route('/cashflow')
def cashflow_dashboard():
    try:
        cuentas = CuentaBancaria.query.all()
        categorias = CategoriaTransaccion.query.all()
        transacciones = Transaccion.query.order_by(Transaccion.fecha.desc()).all()
        
        # Calcular totales con validación
        total_ingresos = sum(t.monto for t in transacciones if t.tipo == 'ingreso' and t.monto is not None)
        total_gastos = sum(t.monto for t in transacciones if t.tipo == 'gasto' and t.monto is not None)
        
        # Calcular el saldo total de las cuentas bancarias
        saldo_cuentas = sum(c.saldo_actual for c in cuentas if c.saldo_actual is not None)
        
        # El balance ahora incluye el saldo de las cuentas + ingresos - gastos
        balance = saldo_cuentas + total_ingresos - total_gastos
        
        # Validar saldos de cuentas
        for cuenta in cuentas:
            if cuenta.saldo_actual is None:
                cuenta.saldo_actual = 0.0
                db.session.add(cuenta)
        
        db.session.commit()
        
        return render_template('cashflow/dashboard.html', 
                             cuentas=cuentas, 
                             categorias=categorias, 
                             transacciones=transacciones,
                             total_ingresos=total_ingresos,
                             total_gastos=total_gastos,
                             balance=balance,
                             saldo_cuentas=saldo_cuentas)
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/cashflow/cuentas', methods=['GET', 'POST'])
def gestionar_cuentas():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            tipo = request.form['tipo']
            saldo_inicial = float(request.form.get('saldo_inicial', 0))
            
            if saldo_inicial < 0:
                flash('El saldo inicial no puede ser negativo', 'error')
                return redirect(url_for('gestionar_cuentas'))
            
            nueva_cuenta = CuentaBancaria(
                nombre=nombre,
                tipo=tipo,
                saldo_actual=saldo_inicial
            )
            
            db.session.add(nueva_cuenta)
            db.session.commit()
            
            flash('Cuenta creada correctamente', 'success')
            return redirect(url_for('cashflow_dashboard'))
        except ValueError:
            flash('El saldo inicial debe ser un número válido', 'error')
            return redirect(url_for('gestionar_cuentas'))
        except Exception as e:
            flash(f'Error al crear la cuenta: {str(e)}', 'error')
            return redirect(url_for('gestionar_cuentas'))
    
    cuentas = CuentaBancaria.query.all()
    return render_template('cashflow/cuentas.html', cuentas=cuentas)

@app.route('/cashflow/categorias', methods=['GET', 'POST'])
def gestionar_categorias():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            tipo = request.form['tipo']
            descripcion = request.form.get('descripcion')
            
            nueva_categoria = CategoriaTransaccion(
                nombre=nombre,
                tipo=tipo,
                descripcion=descripcion
            )
            
            db.session.add(nueva_categoria)
            db.session.commit()
            
            flash('Categoría creada correctamente', 'success')
            return redirect(url_for('cashflow_dashboard'))
        except Exception as e:
            flash(f'Error al crear la categoría: {str(e)}', 'error')
            return redirect(url_for('gestionar_categorias'))
    
    categorias = CategoriaTransaccion.query.all()
    return render_template('cashflow/categorias.html', categorias=categorias)

@app.route('/cashflow/transacciones', methods=['GET', 'POST'])
def gestionar_transacciones():
    if request.method == 'POST':
        try:
            cuenta_id = request.form['cuenta_id']
            categoria_id = request.form['categoria_id']
            fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
            monto = float(request.form['monto'])
            tipo = request.form['tipo']
            descripcion = request.form.get('descripcion')
            
            if monto <= 0:
                flash('El monto debe ser mayor a 0', 'error')
                return redirect(url_for('gestionar_transacciones'))
            
            # Validar que la cuenta existe
            cuenta = CuentaBancaria.query.get(cuenta_id)
            if not cuenta:
                flash('La cuenta seleccionada no existe', 'error')
                return redirect(url_for('gestionar_transacciones'))
            
            # Validar que la categoría existe
            categoria = CategoriaTransaccion.query.get(categoria_id)
            if not categoria:
                flash('La categoría seleccionada no existe', 'error')
                return redirect(url_for('gestionar_transacciones'))
            
            # Validar que el tipo de transacción coincide con la categoría
            if categoria.tipo != tipo:
                flash('El tipo de transacción no coincide con la categoría seleccionada', 'error')
                return redirect(url_for('gestionar_transacciones'))
            
            # Manejar comprobante si se subió uno
            comprobante = None
            if 'comprobante' in request.files:
                archivo = request.files['comprobante']
                if archivo.filename:
                    filename = secure_filename(archivo.filename)
                    # Asegurarse de que el directorio existe
                    comprobantes_dir = os.path.join('static', 'comprobantes')
                    os.makedirs(comprobantes_dir, exist_ok=True)
                    # Guardar el archivo
                    archivo.save(os.path.join(comprobantes_dir, filename))
                    comprobante = filename
            
            nueva_transaccion = Transaccion(
                cuenta_id=cuenta_id,
                categoria_id=categoria_id,
                fecha=fecha,
                monto=monto,
                tipo=tipo,
                descripcion=descripcion,
                comprobante=comprobante
            )
            
            db.session.add(nueva_transaccion)
            nueva_transaccion.aplicar_transaccion()
            db.session.commit()
            
            flash('Transacción registrada correctamente', 'success')
            return redirect(url_for('cashflow_dashboard'))
        except ValueError:
            flash('Los datos ingresados no son válidos', 'error')
            return redirect(url_for('gestionar_transacciones'))
        except Exception as e:
            flash(f'Error al registrar la transacción: {str(e)}', 'error')
            return redirect(url_for('gestionar_transacciones'))
    
    cuentas = CuentaBancaria.query.all()
    categorias = CategoriaTransaccion.query.all()
    transacciones = Transaccion.query.order_by(Transaccion.fecha.desc()).all()
    return render_template('cashflow/transacciones.html', 
                         cuentas=cuentas, 
                         categorias=categorias, 
                         transacciones=transacciones)

@app.route('/cashflow/exportar-reporte')
def exportar_reporte_financiero():
    try:
        # Obtener datos para el reporte dentro del contexto de la aplicación
        with app.app_context():
            # Obtener datos para el reporte
            transacciones = Transaccion.query.order_by(Transaccion.fecha).all()
            cuentas = CuentaBancaria.query.all()
            categorias = CategoriaTransaccion.query.all()
            
            # Crear el reporte en Google Sheets
            exito, mensaje = backup_drive.exportar_reporte_financiero(
                transacciones=transacciones,
                cuentas=cuentas,
                categorias=categorias
            )
            
            if exito:
                # Extraer el enlace del mensaje
                enlace_match = re.search(r'Enlace: (https://docs\.google\.com/spreadsheets/d/.*?/edit)', mensaje)
                if enlace_match:
                    enlace = enlace_match.group(1)
                    flash('Reporte financiero exportado correctamente.', 'success')
                    # Redirigir al usuario al enlace del reporte
                    return redirect(enlace)
                else:
                    flash(f'Reporte financiero exportado correctamente. {mensaje}', 'success')
            else:
                flash(f'Error al exportar reporte: {mensaje}', 'error')
            
            # Si no se pudo extraer el enlace o hubo un error, redirigir al dashboard
            return redirect(url_for('cashflow_dashboard'))
    except Exception as e:
        flash(f'Error al exportar reporte: {str(e)}', 'error')
        return redirect(url_for('cashflow_dashboard'))

@app.route('/cashflow/transacciones/eliminar/<int:id>')
def eliminar_transaccion(id):
    try:
        transaccion = Transaccion.query.get_or_404(id)
        
        # Obtener la cuenta asociada a la transacción
        cuenta = transaccion.cuenta
        
        # Revertir el saldo de la cuenta
        if transaccion.tipo == 'ingreso':
            cuenta.saldo_actual -= transaccion.monto
        else:  # tipo == 'gasto'
            cuenta.saldo_actual += transaccion.monto
        
        # Eliminar la transacción
        db.session.delete(transaccion)
        db.session.commit()
        
        flash('Transacción eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la transacción: {str(e)}', 'error')
    
    return redirect(url_for('cashflow_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)