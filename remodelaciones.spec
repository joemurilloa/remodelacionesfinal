# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Crear directorio de salida personalizado
output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'SistemaCotizaciones')
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('credentials.json', '.'),
        ('token.json', '.'),
        ('sistema_cotizaciones.db', '.'),
        ('config.py', '.'),
        ('backup_drive.py', '.'),
        ('pdf_generator.py', '.'),
        ('models.py', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'reportlab',
        'google.oauth2.credentials',
        'google_auth_oauthlib.flow',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'pydrive2',
        'config',
        'backup_drive',
        'pdf_generator',
        'models',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Sistema de Cotizaciones',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico',
    distpath=output_dir
) 