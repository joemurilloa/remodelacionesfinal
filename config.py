import os
import sys

def get_base_path():
    """Obtiene la ruta base de la aplicación."""
    if getattr(sys, 'frozen', False):
        # Si estamos ejecutando como un ejecutable
        return os.path.dirname(sys.executable)
    else:
        # Si estamos ejecutando como script
        return os.path.dirname(os.path.abspath(__file__))

# Rutas de archivos
BASE_PATH = get_base_path()
CREDENTIALS_FILE = os.path.join(BASE_PATH, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_PATH, 'token.json')
DB_FILE = os.path.join(BASE_PATH, 'sistema_cotizaciones.db')
BACKUP_DIR = os.path.join(BASE_PATH, 'backups')
TEMPLATES_DIR = os.path.join(BASE_PATH, 'templates')
STATIC_DIR = os.path.join(BASE_PATH, 'static')

# Configuración de Google Drive
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]
BACKUP_FOLDER_NAME = 'sistema_cotizaciones_backups'
COTIZACIONES_FOLDER_NAME = 'cotizaciones'
FACTURAS_FOLDER_NAME = 'facturas'
MAX_BACKUPS = 20 