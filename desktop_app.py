import os
import sys
import webbrowser
from threading import Timer
from app import app
from config import *

def open_browser():
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == '__main__':
    # Configurar las rutas de la aplicación
    app.template_folder = TEMPLATES_DIR
    app.static_folder = STATIC_DIR

    # Abrir el navegador después de 1.5 segundos
    Timer(1.5, open_browser).start()
    
    # Iniciar la aplicación Flask
    app.run(debug=False) 