from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health(request):
    """
    Endpoint de prueba rápida.
    GET https://proteccion-pdf.onrender.com/api/health/
    """
    return JsonResponse(
        {"status": "ok", "message": "Proteccion PDF activo (DEBUG)"},
        status=200,
    )


@csrf_exempt
def proteger_pdf(request):
    """
    SOLO DEBUG por ahora.
    Nos devuelve exactamente lo que está recibiendo el servidor.
    """
    raw = request.body or b""

    try:
        raw_text = raw.decode("utf-8", errors="replace")
    except Exception:
        raw_text = "<no se pudo decodificar como utf-8>"

    return JsonResponse(
        {
            "debug": True,
            "method": request.method,
            "content_type_header": request.headers.get(
                "Content-Type", "SIN CONTENT-TYPE"
            ),
            "raw_bytes_length": len(raw),
            "raw_body_first_500": raw_text[:500],
        },
        status=200,
    )
