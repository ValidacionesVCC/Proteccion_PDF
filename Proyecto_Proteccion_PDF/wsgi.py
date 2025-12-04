"""
WSGI config for Proyecto_Proteccion_PDF project.

This exposes the WSGI callable as a module-level variable named `application`.
"""

import os
from django.core.wsgi import get_wsgi_application

# Esta ES tu única app válida
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_Proteccion_PDF.settings')

application = get_wsgi_application()
