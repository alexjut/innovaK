# apps/kactivo/services/onedrive_upload.py

import requests
import logging
from django.conf import settings

# Configura tu logger si no lo tienes
logger = logging.getLogger(__name__)

# ============================================
# Función: subir_a_onedrive
# Descripción: Sube un archivo a OneDrive vía API (o similar)
# Parámetros:
#   - archivo: objeto File cargado desde Django
#   - nombre_archivo: nombre con el que se guardará en OneDrive
# Retorno:
#   - URL de descarga si exitoso
#   - None si hay error
# ============================================

def subir_a_onedrive(archivo, nombre_archivo):
    """
    Sube un archivo a OneDrive usando una integración externa.

    :param archivo: archivo tipo File recibido desde un formulario
    :param nombre_archivo: nombre deseado en OneDrive
    :return: URL del archivo si se subió correctamente, None si hubo error
    """
    try:
        # Ejemplo: endpoint de subida
        url_api = settings.ONEDRIVE_UPLOAD_URL  # debe estar en tu settings
        token = settings.ONEDRIVE_TOKEN         # o maneja OAuth

        # Preparamos headers y archivo para envío
        headers = {
            'Authorization': f'Bearer {token}'
        }

        files = {
            'file': (nombre_archivo, archivo.read())
        }

        response = requests.post(url_api, headers=headers, files=files)

        if response.status_code == 200:
            # Extraer URL o ID según tu API
            data = response.json()
            url_final = data.get("file_url") or data.get("webUrl")  # depende del API real
            logger.info(f"Archivo subido a OneDrive: {url_final}")
            return url_final
        else:
            logger.error(f"Error al subir archivo: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.exception(f"Excepción al subir archivo a OneDrive: {str(e)}")
        return None
