import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# ======================================================
#   ENDPOINT DE PRUEBA
# ======================================================
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Proteccion PDF activo"})


# ======================================================
#   ENDPOINT DE DIAGNÓSTICO (EL QUE VAMOS A USAR HOY)
# ======================================================
@csrf_exempt
def proteger_pdf(request):
    """
    Este endpoint NO procesa PDF.
    Su único objetivo es MOSTRAR EXACTAMENTE
    lo que Power Automate está enviando.
    """

    try:
        raw = request.body

        # Intentar decodificar JSON si corresponde
        json_detected = None
        try:
            json_detected = json.loads(raw.decode("utf-8"))
        except Exception:
            json_detected = "NO ES JSON — ES RAW BINARIO"

        return JsonResponse(
            {
                "raw_bytes_length": len(raw),
                "raw_body_preview_utf8": raw[:300].decode("utf-8", errors="ignore"),
                "full_raw_body_utf8": raw.decode("utf-8", errors="ignore"),
                "content_type_header": request.headers.get("Content-Type", "NO CONTENT-TYPE"),
                "json_detected": json_detected,
                "mensaje": "ESTO es exactamente lo que Power Automate está enviando"
            },
            status=200,
        )

    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


# ======================================================
#   ENDPOINT ORIGINAL (DESACTIVADO — SOLO REFERENCIA)
# ======================================================
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

