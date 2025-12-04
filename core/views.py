import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# ==============================================================
#           ENDPOINT DE PRUEBA (CONFIRMAR QUE CARGA)
# ==============================================================

@csrf_exempt
def proteger_pdf(request):
    """
    PRUEBA DEFINITIVA:
    Esto debe responder SIEMPRE:
    {"test": "ESTE ES EL CODIGO NUEVO"}

    Si Render NO devuelve esto,
    entonces NO está usando este archivo.
    """
    return JsonResponse({"test": "ESTE ES EL CODIGO NUEVO"}, status=200)


# ==============================================================
#               ENDPOINT DE SALUD DEL SERVICIO
# ==============================================================

@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Proteccion PDF activo"})
