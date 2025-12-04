import base64
import json
import io

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes


# ======================================================
# TEST / SALUD
# ======================================================
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ======================================================
# ENDPOINT DE DIAGNÓSTICO (LO QUE TENÍAS)
# ======================================================
@csrf_exempt
def proteger_pdf(request):
    """
    Endpoint de diagnóstico: solo devuelve información
    de lo que está enviando Power Automate.
    """
    try:
        raw = request.body

        try:
            json_detected = json.loads(raw.decode("utf-8"))
        except Exception:
            json_detected = "NO ES JSON — ES RAW BINARIO"

        return JsonResponse(
            {
                "raw_bytes_length": len(raw),
                "content_type_header": request.headers.get("Content-Type", "NO CONTENT-TYPE"),
                "json_detected": json_detected,
                "mensaje": "Diagnóstico del contenido recibido desde Power Automate",
            },
            status=200,
        )

    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


# ======================================================
# CONVERTIR PDF → IMÁGENES (ESTE ES EL QUE USAREMOS)
# ======================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    """
    Espera un JSON como:
    {
        "$content": "<PDF_EN_BASE64>"
    }

    Devuelve:
    {
        "total_paginas": N,
        "imagenes": [
            { "pagina": 1, "imagen_base64": "..." },
            ...
        ]
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # 1) Leer body como texto
        raw_text = request.body.decode("utf-8", errors="ignore")

        # 2) Parsear JSON
        try:
            data = json.loads(raw_text)
        except Exception:
            return JsonResponse(
                {"error": "Power Automate debe enviar JSON válido con '$content'."},
                status=400,
            )

        if "$content" not in data:
            return JsonResponse(
                {"error": "No se recibió '$content' desde Power Automate."},
                status=400,
            )

        # 3) Decodificar PDF desde base64
        try:
            pdf_bytes = base64.b64decode(data["$content"])
        except Exception as exc:
            return JsonResponse(
                {"error": f"No se pudo decodificar el base64 del PDF: {str(exc)}"},
                status=400,
            )

        if not pdf_bytes.startswith(b"%PDF"):
            return JsonResponse(
                {"error": "El contenido recibido NO es un PDF válido."},
                status=400,
            )

        # 4) Convertir PDF a imágenes
        imagenes = convert_from_bytes(pdf_bytes)

        lista_base64 = []
        for i, img in enumerate(imagenes):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=92)
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            lista_base64.append(
                {
                    "pagina": i + 1,
                    "imagen_base64": img_b64,
                }
            )

        # 5) Respuesta para Power Automate
        return JsonResponse(
            {
                "total_paginas": len(lista_base64),
                "imagenes": lista_base64,
            },
            status=200,
        )

    except Exception as exc:
        return JsonResponse(
            {"error": f"Error interno en el servidor: {str(exc)}"},
            status=500,
        )

