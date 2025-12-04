import base64
import json
import io
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes

# ======================
# HEALTH CHECK (OBLIGATORIO)
# ======================
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})

# ======================
# CONVERTIR PDF A IMÁGENES
# ======================
@csrf_exempt
def convertir_pdf_imagenes(request):

    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        raw = request.body.decode("utf-8", errors="ignore")

        try:
            data = json.loads(raw)
        except:
            return JsonResponse(
                {"error": "Power Automate debe enviar JSON válido con '$content'."},
                status=400,
            )

        if "$content" not in data:
            return JsonResponse({"error": "No se recibió '$content'."}, status=400)

        pdf_bytes = base64.b64decode(data["$content"])

        if not pdf_bytes.startswith(b"%PDF"):
            return JsonResponse({"error": "El archivo no es PDF válido."}, status=400)

        imagenes = convert_from_bytes(pdf_bytes)

        lista = []
        for i, img in enumerate(imagenes):
            buff = io.BytesIO()
            img.save(buff, format="JPEG", quality=92)
            b64 = base64.b64encode(buff.getvalue()).decode()

            lista.append({
                "pagina": i + 1,
                "imagen_base64": b64
            })

        return JsonResponse({
            "total_paginas": len(lista),
            "imagenes": lista
        })

    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
