import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def proteger_pdf(request):
    try:
        raw = request.body

        return JsonResponse({
            "raw_bytes_length": len(raw),
            "raw_body_as_text": raw.decode("utf-8", errors="ignore")[:5000],
            "content_type_header": request.headers.get("Content-Type", "NO HEADER"),
            "message": "Esto es EXACTAMENTE lo que está enviando Power Automate."
        }, status=200)

    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)



# =====================================================
#   ESTA ES LA FUNCIÓN QUE PEDISTE REEMPLAZAR
# =====================================================
@csrf_exempt
def proteger_pdf(request):
    return JsonResponse({"test": "ESTE ES EL CODIGO NUEVO"}, status=200)


# =====================================================
#  ESTA ES LA FUNCIÓN ORIGINAL (NO USADA AHORA)
#  *Te la dejo abajo intacta por si quieres volver a usarla*
# =====================================================

@csrf_exempt
def proteger_pdf_original(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        raw_body = request.body

        if not raw_body:
            return JsonResponse({"error": "El cuerpo está vacío"}, status=400)

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return JsonResponse(
                {
                    "error": (
                        "Power Automate envió un formato incorrecto. "
                        "Debe ser JSON con '$content' y '$content-type'."
                    )
                },
                status=400,
            )

        content_b64 = data.get("$content")
        content_type = data.get("$content-type", "").lower()

        if not content_b64:
            return JsonResponse(
                {"error": "No se recibió '$content' desde Power Automate."},
                status=400,
            )

        if "pdf" not in content_type:
            return JsonResponse(
                {"error": "El archivo recibido NO es PDF."},
                status=400,
            )

        try:
            pdf_bytes = base64.b64decode(content_b64)
        except Exception as exc:
            return JsonResponse(
                {"error": f"No se pudo decodificar el base64: {str(exc)}"},
                status=400,
            )

        if not pdf_bytes.startswith(b"%PDF"):
            return JsonResponse(
                {"error": "El contenido decodificado NO es un PDF válido."},
                status=400,
            )

        processed_pdf_bytes = pdf_bytes

        processed_b64 = base64.b64encode(processed_pdf_bytes).decode("utf-8")

        return JsonResponse(
            {
                "$content-type": "application/pdf",
                "$content": processed_b64,
            },
            status=200,
        )

    except Exception as exc:
        return JsonResponse(
            {"error": f"Error interno: {str(exc)}"},
            status=500,
        )

