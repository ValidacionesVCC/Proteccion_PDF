import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_Proteccion_PDF.settings')

application = get_asgi_application()
