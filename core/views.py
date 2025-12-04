import base64
import json
import io
import zipfile
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes


# ======================================================
# TEST
# ======================================================
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ======================================================
# CONVERTIR PDF → IMÁGENES (LISTA BASE64)
# ======================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # ---------------------------------------------
        # 1️⃣ RECIBIR JSON DESDE POWER AUTOMATE
        # ---------------------------------------------
        raw = request.body.decode("utf-8", errors="ignore")

        try:
            data = json.loads(raw)
        except:
            return JsonResponse({"error": "Formato incorrecto. Power Automate debe enviar JSON con '$content'."}, status=400)

        if "$content" not in data:
            return JsonResponse({"error": "No se recibió '$content' desde Power Automate."}, status=400)

        # ---------------------------------------------
        # 2️⃣ DECODIFICAR PDF DESDE BASE64
        # ---------------------------------------------
        pdf_bytes = base64.b64decode(data["$content"])

        if not pdf_bytes.startswith(b"%PDF"):
            return JsonResponse({"error": "El contenido recibido NO es un PDF válido."}, status=400)

        # ---------------------------------------------
        # 3️⃣ CONVERTIR PDF EN LISTA DE IMÁGENES
        # ---------------------------------------------
        imagenes = convert_from_bytes(pdf_bytes)

        lista_base64 = []
        for i, img in enumerate(imagenes):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=92)
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            lista_base64.append({
                "pagina": i + 1,
                "imagen_base64": img_b64
            })

        # ---------------------------------------------
        # 4️⃣ RESPUESTA CORRECTA PARA POWER AUTOMATE
        # ---------------------------------------------
        return JsonResponse(
            {
                "total_paginas": len(lista_base64),
                "imagenes": lista_base64
            },
            status=200
        )

    except Exception as exc:
        return JsonResponse({"error": f"Error interno: {str(exc)}"}, status=500)
