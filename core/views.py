import base64
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes


# ---------------------------------------------------------
# ENDPOINT DE SALUD
# ---------------------------------------------------------
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ---------------------------------------------------------
# ENDPOINT PRINCIPAL: Convertir PDF a imágenes
# ---------------------------------------------------------
@csrf_exempt
def convertir_pdf_imagenes(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # Obtener JSON del body
        data = request.json if hasattr(request, "json") else None
        if data is None:
            # Django no parsea automáticamente JSON; debemos hacerlo manualmente
            import json
            body_unicode = request.body.decode("utf-8")
            data = json.loads(body_unicode)

        # Validaciones
        if "content" not in data:
            return JsonResponse({"error": "El JSON debe incluir 'content' (PDF en base64)"}, status=400)

        # Base64 del PDF
        pdf_base64 = data["content"]

        try:
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception:
            return JsonResponse({"error": "Base64 inválido"}, status=400)

        # Convertir PDF a imágenes
        images = convert_from_bytes(pdf_bytes, dpi=200)

        imagenes_respuesta = []
        pagina = 1

        # Convertimos cada página a base64
        for img in images:
            with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
                img.save(tmp.name, "JPEG")
                with open(tmp.name, "rb") as f:
                    imagen_base64 = base64.b64encode(f.read()).decode("utf-8")

            imagenes_respuesta.append({
                "pagina": pagina,
                "imagen_base64": imagen_base64
            })
            pagina += 1

        return JsonResponse({"imagenes": imagenes_respuesta}, status=200)

    except Exception as e:
        # Captura errores inesperados
        return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)
