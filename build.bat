@echo off
pyinstaller --onefile ^
--windowed ^
--add-data "templates;templates" ^
--add-data "static;static" ^
--add-data "credentials.json;." ^
--add-data "token.json;." ^
--add-data "sistema_cotizaciones.db;." ^
--hidden-import flask ^
--hidden-import flask_sqlalchemy ^
--hidden-import reportlab ^
--hidden-import google.oauth2.credentials ^
--hidden-import google_auth_oauthlib.flow ^
--hidden-import googleapiclient.discovery ^
--hidden-import googleapiclient.errors ^
--hidden-import pydrive2 ^
--name "Sistema de Cotizaciones" ^
desktop_app.py
pause 