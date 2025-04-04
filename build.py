import PyInstaller.__main__
import os

# Obtener la ruta actual
current_dir = os.path.dirname(os.path.abspath(__file__))

# Configurar los parámetros de PyInstaller
params = [
    'desktop_app.py',
    '--onefile',
    '--windowed',
    f'--add-data={os.path.join(current_dir, "templates")};templates',
    f'--add-data={os.path.join(current_dir, "static")};static',
    f'--add-data={os.path.join(current_dir, "credentials.json")};.',
    f'--add-data={os.path.join(current_dir, "token.json")};.',
    f'--add-data={os.path.join(current_dir, "sistema_cotizaciones.db")};.',
    '--hidden-import=flask',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=reportlab',
    '--hidden-import=google.oauth2.credentials',
    '--hidden-import=google_auth_oauthlib.flow',
    '--hidden-import=googleapiclient.discovery',
    '--hidden-import=googleapiclient.errors',
    '--hidden-import=pydrive2',
    '--name=Sistema de Cotizaciones',
]

# Ejecutar PyInstaller
PyInstaller.__main__.run(params) 