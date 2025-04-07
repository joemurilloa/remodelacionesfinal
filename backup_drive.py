import os
import shutil
import datetime
import csv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
import json
from config import *

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(BASE_PATH, 'backup_log.txt')
)

# Configuración de Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
BACKUP_FOLDER_NAME = 'sistema_cotizaciones_backups'
COTIZACIONES_FOLDER_NAME = 'cotizaciones'
FACTURAS_FOLDER_NAME = 'facturas'
BACKUP_DIR = 'backups'
DB_FILE = 'sistema_cotizaciones.db'
MAX_BACKUPS = 20  # Máximo número de backups a mantener

def autenticar_drive():
    """Autentica y devuelve un servicio de Google Drive."""
    creds = None
    
    # Verificar si hay un token guardado
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_info(
            json.loads(open(TOKEN_FILE).read()), SCOPES)
    
    # Si no hay credenciales o no son válidas, autenticar
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Asegurar que el archivo de credenciales existe
            if not os.path.exists(CREDENTIALS_FILE):
                logging.error(f"Archivo de credenciales {CREDENTIALS_FILE} no encontrado")
                raise FileNotFoundError(f"Archivo de credenciales {CREDENTIALS_FILE} no encontrado")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar credenciales para la próxima vez
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def obtener_o_crear_carpeta(service, folder_name, parent_id=None):
    """Obtiene o crea una carpeta en Google Drive."""
    # Construir la consulta para buscar la carpeta
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    response = service.files().list(q=query, spaces='drive',
                                  fields='files(id, name)').execute()
    folders = response.get('files', [])
    
    # Si la carpeta existe, devolver su ID
    if folders:
        folder_id = folders[0]['id']
        logging.info(f"Carpeta '{folder_name}' encontrada: {folder_id}")
        return folder_id
    
    # Si no existe, crear la carpeta
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = folder.get('id')
    logging.info(f"Carpeta '{folder_name}' creada: {folder_id}")
    
    return folder_id

def obtener_o_crear_carpeta_backup(service):
    """Obtiene o crea la carpeta principal de backups en Google Drive."""
    return obtener_o_crear_carpeta(service, BACKUP_FOLDER_NAME)

def obtener_o_crear_subcarpeta(service, nombre, parent_id):
    """Obtiene o crea una subcarpeta dentro de la carpeta principal."""
    return obtener_o_crear_carpeta(service, nombre, parent_id)

def limpiar_backups_antiguos(service, folder_id):
    """Elimina backups antiguos manteniendo solo los últimos MAX_BACKUPS."""
    # Obtener todos los archivos en la carpeta de backup
    query = f"'{folder_id}' in parents and trashed=false"
    response = service.files().list(q=query, spaces='drive',
                                  fields='files(id, name, createdTime)',
                                  orderBy='createdTime').execute()
    files = response.get('files', [])
    
    # Si hay más archivos que el límite, eliminar los más antiguos
    if len(files) > MAX_BACKUPS:
        # Ordenar por fecha de creación (el más antiguo primero)
        files.sort(key=lambda x: x['createdTime'])
        
        # Eliminar los archivos más antiguos
        for file in files[:-MAX_BACKUPS]:
            service.files().delete(fileId=file['id']).execute()
            logging.info(f"Backup antiguo eliminado: {file['name']}")

def exportar_clientes_a_csv():
    """Exporta los clientes a un archivo CSV en Google Drive."""
    from flask import current_app
    from models import Cliente
    
    try:
        # Crear directorio temporal si no existe
        if not os.path.exists('temp'):
            os.makedirs('temp')
        
        # Nombre del archivo CSV
        csv_filename = os.path.join('temp', 'clientes.csv')
        
        # Obtener clientes de la base de datos
        with current_app.app_context():
            clientes = Cliente.query.all()
        
        # Escribir datos en CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'Nombre', 'Email', 'Teléfono', 'Dirección', 'Fecha de Creación']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for cliente in clientes:
                writer.writerow({
                    'ID': cliente.id,
                    'Nombre': cliente.nombre,
                    'Email': cliente.email or '',
                    'Teléfono': cliente.telefono or '',
                    'Dirección': cliente.direccion or '',
                    'Fecha de Creación': cliente.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if cliente.fecha_creacion else ''
                })
        
        # Subir el archivo a Google Drive
        service = autenticar_drive()
        
        # Obtener la carpeta principal de backups
        folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Buscar si ya existe un archivo CSV de clientes
        query = f"name='clientes.csv' and '{folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        
        file_metadata = {
            'name': 'clientes.csv',
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(csv_filename, mimetype='text/csv', resumable=True)
        
        # Actualizar o crear el archivo
        if files:
            file_id = files[0]['id']
            file = service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id'
            ).execute()
            logging.info(f"CSV de clientes actualizado en Google Drive: {file.get('id')}")
        else:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            logging.info(f"CSV de clientes creado en Google Drive: {file.get('id')}")
        
        # Limpiar archivo temporal
        os.remove(csv_filename)
        
        return True, "Archivo CSV de clientes exportado correctamente a Google Drive."
    except Exception as e:
        logging.error(f"Error al exportar clientes a CSV: {str(e)}")
        return False, f"Error al exportar clientes: {str(e)}"

def exportar_clientes_a_sheets(cliente_nuevo=None):
    """Exporta los clientes a una hoja de Google Sheets.
    
    Args:
        cliente_nuevo: Si se proporciona, solo se añadirá este cliente como una nueva fila.
                      Si es None, se exportarán todos los clientes.
    """
    from flask import current_app
    from models import Cliente
    
    try:
        # Autenticar con Google
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_info(
                json.loads(open(TOKEN_FILE).read()), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        # Crear servicios
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Obtener o crear la carpeta principal
        folder_id = obtener_o_crear_carpeta_backup(drive_service)
        
        # Buscar si ya existe una hoja de cálculo
        query = f"name='clientes' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        
        if files:
            spreadsheet_id = files[0]['id']
        else:
            # Crear nueva hoja de cálculo
            file_metadata = {
                'name': 'clientes',
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [folder_id]
            }
            file = drive_service.files().create(body=file_metadata, fields='id').execute()
            spreadsheet_id = file.get('id')
            
            # Configurar encabezados
            headers = [['ID', 'Nombre','Email', 'Teléfono', 'Dirección', 'Fecha de Creación']]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
        
        # Preparar datos para la hoja
        values = []
        
        if cliente_nuevo:
            # Si se proporciona un cliente específico, solo añadir ese cliente
            values.append([
                cliente_nuevo.id,
                cliente_nuevo.nombre,
                cliente_nuevo.email or '',
                cliente_nuevo.telefono or '',
                cliente_nuevo.direccion or '',
                cliente_nuevo.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if cliente_nuevo.fecha_creacion else ''
            ])
        else:
            # Si no se proporciona un cliente específico, obtener todos los clientes
            with current_app.app_context():
                clientes = Cliente.query.all()
            
            for cliente in clientes:
                values.append([
                    cliente.id,
                    cliente.nombre,
                    cliente.email or '',
                    cliente.telefono or '',
                    cliente.direccion or '',
                    cliente.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if cliente.fecha_creacion else ''
                ])
        
        # Obtener la última fila con datos
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A:A'
        ).execute()
        last_row = len(result.get('values', []))
        
        # Añadir nuevos datos
        if values:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'A{last_row + 1}',
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
        
        logging.info(f"Clientes exportados correctamente a Google Sheets: {spreadsheet_id}")
        return True, "Clientes exportados correctamente a Google Sheets."
    except Exception as e:
        logging.error(f"Error al exportar clientes a Google Sheets: {str(e)}")
        return False, f"Error al exportar clientes: {str(e)}"

def sincronizar_pdfs_cotizaciones():
    """Sincroniza los PDFs de cotizaciones con Google Drive."""
    try:
        # Directorio donde se almacenan los PDFs
        pdf_dir = os.path.join('static', 'pdfs')
        if not os.path.exists(pdf_dir):
            return False, "El directorio de PDFs no existe."
        
        # Autenticar con Google Drive
        service = autenticar_drive()
        
        # Obtener la carpeta principal
        main_folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Obtener o crear la subcarpeta de cotizaciones
        cotizaciones_folder_id = obtener_o_crear_subcarpeta(service, COTIZACIONES_FOLDER_NAME, main_folder_id)
        
        # Obtener lista de archivos en Drive
        query = f"'{cotizaciones_folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        drive_files = {file['name']: file['id'] for file in response.get('files', [])}
        
        # Listar PDFs locales de cotizaciones
        pdfs_cotizaciones = [f for f in os.listdir(pdf_dir) if f.startswith('cotizacion_') and f.endswith('.pdf')]
        
        # Contadores para estadísticas
        nuevos = 0
        actualizados = 0
        
        # Sincronizar cada PDF
        for pdf_name in pdfs_cotizaciones:
            pdf_path = os.path.join(pdf_dir, pdf_name)
            
            file_metadata = {
                'name': pdf_name,
                'parents': [cotizaciones_folder_id]
            }
            
            media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
            
            # Actualizar o crear el archivo
            if pdf_name in drive_files:
                file = service.files().update(
                    fileId=drive_files[pdf_name],
                    media_body=media,
                    fields='id'
                ).execute()
                actualizados += 1
            else:
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                nuevos += 1
        
        mensaje = f"Sincronización de cotizaciones completada: {nuevos} nuevos, {actualizados} actualizados."
        logging.info(mensaje)
        return True, mensaje
    except Exception as e:
        logging.error(f"Error al sincronizar PDFs de cotizaciones: {str(e)}")
        return False, f"Error al sincronizar cotizaciones: {str(e)}"

def sincronizar_pdfs_facturas():
    """Sincroniza los PDFs de facturas con Google Drive."""
    try:
        # Directorio donde se almacenan los PDFs
        pdf_dir = os.path.join('static', 'pdfs')
        if not os.path.exists(pdf_dir):
            return False, "El directorio de PDFs no existe."
        
        # Autenticar con Google Drive
        service = autenticar_drive()
        
        # Obtener la carpeta principal
        main_folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Obtener o crear la subcarpeta de facturas
        facturas_folder_id = obtener_o_crear_subcarpeta(service, FACTURAS_FOLDER_NAME, main_folder_id)
        
        # Obtener lista de archivos en Drive
        query = f"'{facturas_folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        drive_files = {file['name']: file['id'] for file in response.get('files', [])}
        
        # Listar PDFs locales de facturas
        pdfs_facturas = [f for f in os.listdir(pdf_dir) if f.startswith('factura_') and f.endswith('.pdf')]
        
        # Contadores para estadísticas
        nuevos = 0
        actualizados = 0
        
        # Sincronizar cada PDF
        for pdf_name in pdfs_facturas:
            pdf_path = os.path.join(pdf_dir, pdf_name)
            
            file_metadata = {
                'name': pdf_name,
                'parents': [facturas_folder_id]
            }
            
            media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
            
            # Actualizar o crear el archivo
            if pdf_name in drive_files:
                file = service.files().update(
                    fileId=drive_files[pdf_name],
                    media_body=media,
                    fields='id'
                ).execute()
                actualizados += 1
            else:
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                nuevos += 1
        
        mensaje = f"Sincronización de facturas completada: {nuevos} nuevas, {actualizados} actualizadas."
        logging.info(mensaje)
        return True, mensaje
    except Exception as e:
        logging.error(f"Error al sincronizar PDFs de facturas: {str(e)}")
        return False, f"Error al sincronizar facturas: {str(e)}"

def realizar_backup_completo():
    """Realiza un backup completo: clientes, cotizaciones y facturas."""
    try:
        resultados = []
        
        # Exportar todos los clientes a Google Sheets
        exito, mensaje = exportar_clientes_a_sheets(cliente_nuevo=None)
        resultados.append(mensaje)
        
        # Sincronizar PDFs de cotizaciones
        exito, mensaje = sincronizar_pdfs_cotizaciones()
        resultados.append(mensaje)
        
        # Sincronizar PDFs de facturas
        exito, mensaje = sincronizar_pdfs_facturas()
        resultados.append(mensaje)
        
        logging.info("Backup completo realizado con éxito")
        return True, "\n".join(resultados)
    except Exception as e:
        logging.error(f"Error en el proceso de backup completo: {str(e)}")
        return False, f"Error en el backup: {str(e)}"

def realizar_backup():
    """Realiza una copia de la base de datos y devuelve la ruta del archivo."""
    # Crear directorio de backups si no existe
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    # Nombre del archivo de backup con timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # Copiar la base de datos actual
    try:
        shutil.copy2(DB_FILE, backup_path)
        logging.info(f"Backup local creado: {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Error al crear backup local: {str(e)}")
        raise

def subir_a_drive(backup_file):
    """Sube el archivo de backup a Google Drive."""
    try:
        # Autenticar con Google Drive
        service = autenticar_drive()
        
        # Obtener o crear carpeta de backups
        folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Nombre del archivo en Google Drive
        file_name = os.path.basename(backup_file)
        
        # Metadata del archivo
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Subir el archivo
        media = MediaFileUpload(backup_file, resumable=True)
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        
        logging.info(f"Backup subido a Google Drive: {file.get('id')}")
        
        # Limpiar backups antiguos
        limpiar_backups_antiguos(service, folder_id)
        
        return file.get('id')
    except Exception as e:
        logging.error(f"Error al subir backup a Google Drive: {str(e)}")
        raise

def exportar_reporte_financiero(transacciones, cuentas, categorias):
    try:
        # Autenticar con Google
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_info(
                json.loads(open(TOKEN_FILE).read()), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        # Crear servicios
        drive_service = build('drive', 'v3', credentials=creds)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Crear un nuevo archivo de Google Sheets
        spreadsheet = {
            'properties': {
                'title': f'Reporte Financiero - {datetime.datetime.now().strftime("%Y-%m-%d")}'
            }
        }
        
        # Crear el archivo en Google Drive
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        
        # Preparar datos para el resumen
        total_ingresos = sum(t.monto for t in transacciones if t.tipo == 'ingreso')
        total_gastos = sum(t.monto for t in transacciones if t.tipo == 'gasto')
        balance = total_ingresos - total_gastos
        
        # Calcular porcentaje de gastos sobre ingresos
        porcentaje_gastos = (total_gastos / total_ingresos * 100) if total_ingresos > 0 else 0
        
        # Calcular saldo total de todas las cuentas
        saldo_total_cuentas = sum(cuenta.saldo_actual for cuenta in cuentas)
        
        # Preparar datos para el resumen financiero
        resumen_data = [
            ['REPORTE FINANCIERO', '', '', ''],
            ['Fecha de generación:', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), '', ''],
            ['', '', '', ''],
            ['RESUMEN FINANCIERO', '', '', ''],
            ['Total Ingresos', '{:,.2f}'.format(total_ingresos), '', ''],
            ['Total Gastos', '{:,.2f}'.format(total_gastos), '', ''],
            ['Balance', '{:,.2f}'.format(balance), '', ''],
            ['Porcentaje de Gastos sobre Ingresos', '{:.2f}%'.format(porcentaje_gastos), '', ''],
            ['', '', '', ''],
            ['SALDOS POR CUENTA', '', '', ''],
            ['Cuenta', 'Tipo', 'Saldo Actual', 'Porcentaje del Total']
        ]
        
        # Añadir datos de cuentas con porcentaje del total
        for cuenta in cuentas:
            porcentaje = (cuenta.saldo_actual / saldo_total_cuentas * 100) if saldo_total_cuentas > 0 else 0
            resumen_data.append([
                cuenta.nombre,
                cuenta.tipo,
                '{:,.2f}'.format(cuenta.saldo_actual),
                '{:.2f}%'.format(porcentaje)
            ])
        
        # Añadir total de saldos
        resumen_data.append([
            'TOTAL', 
            '', 
            '{:,.2f}'.format(saldo_total_cuentas),
            '100.00%'
        ])
        
        # Preparar datos de transacciones
        transacciones_data = [
            ['Fecha', 'Cuenta', 'Categoría', 'Tipo', 'Monto', 'Descripción']
        ]
        
        # Ordenar transacciones por fecha (más recientes primero)
        transacciones_ordenadas = sorted(transacciones, key=lambda x: x.fecha, reverse=True)
        
        for t in transacciones_ordenadas:
            transacciones_data.append([
                t.fecha.strftime('%Y-%m-%d'),
                t.cuenta.nombre,
                t.categoria.nombre,
                t.tipo,
                '{:,.2f}'.format(t.monto),
                t.descripcion or ''
            ])
        
        # Preparar análisis por categoría
        categorias_data = [
            ['Categoría', 'Tipo', 'Total', 'Porcentaje', 'Cantidad de Transacciones']
        ]
        
        # Calcular totales por categoría
        for categoria in categorias:
            transacciones_categoria = [t for t in transacciones if t.categoria_id == categoria.id]
            total = sum(t.monto for t in transacciones_categoria)
            
            # Calcular porcentaje sobre el total de transacciones del mismo tipo
            if categoria.tipo == 'ingreso':
                porcentaje = (total / total_ingresos * 100) if total_ingresos > 0 else 0
            else:
                porcentaje = (total / total_gastos * 100) if total_gastos > 0 else 0
                
            categorias_data.append([
                categoria.nombre,
                categoria.tipo,
                '{:,.2f}'.format(total),
                '{:.2f}%'.format(porcentaje),
                len(transacciones_categoria)
            ])
        
        # Añadir totales por tipo
        categorias_data.append(['TOTAL INGRESOS', 'ingreso', '{:,.2f}'.format(total_ingresos), '100.00%', ''])
        categorias_data.append(['TOTAL GASTOS', 'gasto', '{:,.2f}'.format(total_gastos), '100.00%', ''])
        
        # Preparar análisis mensual
        # Agrupar transacciones por mes
        transacciones_por_mes = {}
        for t in transacciones:
            mes_key = t.fecha.strftime('%Y-%m')
            if mes_key not in transacciones_por_mes:
                transacciones_por_mes[mes_key] = {'ingresos': 0, 'gastos': 0}
            
            if t.tipo == 'ingreso':
                transacciones_por_mes[mes_key]['ingresos'] += t.monto
            else:
                transacciones_por_mes[mes_key]['gastos'] += t.monto
        
        # Ordenar meses
        meses_ordenados = sorted(transacciones_por_mes.keys())
        
        # Preparar datos para análisis mensual
        mensual_data = [
            ['Mes', 'Ingresos', 'Gastos', 'Balance', 'Porcentaje Gastos/Ingresos']
        ]
        
        for mes in meses_ordenados:
            ingresos = transacciones_por_mes[mes]['ingresos']
            gastos = transacciones_por_mes[mes]['gastos']
            balance_mes = ingresos - gastos
            porcentaje = (gastos / ingresos * 100) if ingresos > 0 else 0
            
            # Formatear mes para mejor visualización
            año, mes_num = mes.split('-')
            nombre_mes = datetime.datetime(int(año), int(mes_num), 1).strftime('%B %Y')
            
            mensual_data.append([
                nombre_mes,
                '{:,.2f}'.format(ingresos),
                '{:,.2f}'.format(gastos),
                '{:,.2f}'.format(balance_mes),
                '{:.2f}%'.format(porcentaje)
            ])
        
        # Actualizar las hojas con los datos
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',
            valueInputOption='USER_ENTERED',
            body={'values': resumen_data}
        ).execute()
        
        # Crear nuevas hojas
        body = {
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': 'Transacciones'
                        }
                    }
                },
                {
                    'addSheet': {
                        'properties': {
                            'title': 'Análisis por Categoría'
                        }
                    }
                },
                {
                    'addSheet': {
                        'properties': {
                            'title': 'Análisis Mensual'
                        }
                    }
                }
            ]
        }
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Actualizar datos en las hojas correspondientes
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Transacciones!A1',
            valueInputOption='USER_ENTERED',
            body={'values': transacciones_data}
        ).execute()
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Análisis por Categoría!A1',
            valueInputOption='USER_ENTERED',
            body={'values': categorias_data}
        ).execute()
        
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Análisis Mensual!A1',
            valueInputOption='USER_ENTERED',
            body={'values': mensual_data}
        ).execute()
        
        # Aplicar formato a todas las hojas
        formato_requests = [
            # Formato para el título principal
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,  # Primera hoja (Resumen)
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                            'textFormat': {
                                'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                'fontSize': 16,
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            # Formato para subtítulos
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 3,
                        'endRowIndex': 4
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                            'textFormat': {
                                'fontSize': 14,
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 9,
                        'endRowIndex': 10
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                            'textFormat': {
                                'fontSize': 14,
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            # Formato para encabezados de tabla
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 10,
                        'endRowIndex': 11
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            # Formato para la fila de total
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 10 + len(cuentas),
                        'endRowIndex': 11 + len(cuentas)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            },
            # Formato para encabezados de tabla en otras hojas
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 1,  # Hoja de Transacciones
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 2,  # Hoja de Análisis por Categoría
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            },
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 3,  # Hoja de Análisis Mensual
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            },
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            }
        ]
        
        # Aplicar formato a las filas de totales en la hoja de categorías
        if len(categorias) > 0:
            formato_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': 2,  # Hoja de Análisis por Categoría
                        'startRowIndex': len(categorias) + 1,
                        'endRowIndex': len(categorias) + 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            })
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': formato_requests}
        ).execute()
        
        # Ajustar ancho de columnas
        dimension_requests = [
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 4
                    },
                    'properties': {
                        'pixelSize': 150
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': 1,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 6
                    },
                    'properties': {
                        'pixelSize': 150
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': 2,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 5
                    },
                    'properties': {
                        'pixelSize': 150
                    },
                    'fields': 'pixelSize'
                }
            },
            {
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': 3,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 5
                    },
                    'properties': {
                        'pixelSize': 150
                    },
                    'fields': 'pixelSize'
                }
            }
        ]
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': dimension_requests}
        ).execute()
        
        # Hacer público el archivo para cualquiera con el enlace
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()
        
        # Obtener el enlace para compartir
        file_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
        return True, f'Reporte creado correctamente. Enlace: {file_url}'
    except Exception as e:
        logging.error(f"Error al exportar reporte financiero: {str(e)}")
        return False, str(e)

def subir_pdf_cotizacion(pdf_path):
    """Sube un PDF de cotización específico a Google Drive."""
    try:
        # Autenticar con Google Drive
        service = autenticar_drive()
        
        # Obtener la carpeta principal
        main_folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Obtener o crear la subcarpeta de cotizaciones
        cotizaciones_folder_id = obtener_o_crear_subcarpeta(service, COTIZACIONES_FOLDER_NAME, main_folder_id)
        
        # Preparar el archivo para subir
        file_metadata = {
            'name': os.path.basename(pdf_path),
            'parents': [cotizaciones_folder_id]
        }
        
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        
        # Subir el archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        mensaje = f"PDF de cotización subido correctamente: {os.path.basename(pdf_path)}"
        logging.info(mensaje)
        return True, mensaje
    except Exception as e:
        logging.error(f"Error al subir PDF de cotización: {str(e)}")
        return False, f"Error al subir PDF de cotización: {str(e)}"

def subir_pdf_factura(pdf_path):
    """Sube un PDF de factura específico a Google Drive."""
    try:
        # Autenticar con Google Drive
        service = autenticar_drive()
        
        # Obtener la carpeta principal
        main_folder_id = obtener_o_crear_carpeta_backup(service)
        
        # Obtener o crear la subcarpeta de facturas
        facturas_folder_id = obtener_o_crear_subcarpeta(service, FACTURAS_FOLDER_NAME, main_folder_id)
        
        # Preparar el archivo para subir
        file_metadata = {
            'name': os.path.basename(pdf_path),
            'parents': [facturas_folder_id]
        }
        
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        
        # Subir el archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        mensaje = f"PDF de factura subido correctamente: {os.path.basename(pdf_path)}"
        logging.info(mensaje)
        return True, mensaje
    except Exception as e:
        logging.error(f"Error al subir PDF de factura: {str(e)}")
        return False, f"Error al subir PDF de factura: {str(e)}"

def main():
    """Función principal para ejecutar el backup."""
    try:
        # Realizar backup completo (clientes, cotizaciones, facturas)
        exito, mensaje = realizar_backup_completo()
        
        # También realizar backup de la base de datos (para compatibilidad)
        backup_file = realizar_backup()
        file_id = subir_a_drive(backup_file)
        
        logging.info("Proceso de backup completado con éxito")
        print(f"Backup realizado correctamente.\n{mensaje}\nID en Drive: {file_id}")
        
        return True
    except Exception as e:
        logging.error(f"Error en el proceso de backup: {str(e)}")
        print(f"Error al realizar backup: {str(e)}")
        return False

if __name__ == "__main__":
    # Si se ejecuta directamente, realizar backup
    main()