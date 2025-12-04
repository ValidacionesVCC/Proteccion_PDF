import base64
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Proteccion PDF activo"})


@csrf_exempt
def proteger_pdf(request):
    # SOLO PERMITIMOS POST
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # ------------------------------------------------------------------
        # 1. LEER EL CUERPO BRUTO QUE ENVÍA POWER AUTOMATE
        # ------------------------------------------------------------------
        raw_body = request.body

        if not raw_body:
            return JsonResponse({"error": "El cuerpo está vacío"}, status=400)

        # Power Automate SIEMPRE envía JSON (aunque digas octet-stream)
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

        # ------------------------------------------------------------------
        # 2. EXTRAER EL BASE64 DEL PDF
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # 3. DECODIFICAR BASE64 → BYTES DE PDF
        # ------------------------------------------------------------------
        try:
            pdf_bytes = base64.b64decode(content_b64)
        except Exception as exc:
            return JsonResponse(
                {"error": f"No se pudo decodificar el base64: {str(exc)}"},
                status=400,
            )

        # Validación simple de PDF real
        if not pdf_bytes.startswith(b"%PDF"):
            return JsonResponse(
                {"error": "El contenido decodificado NO es un PDF válido."},
                status=400,
            )

        # ------------------------------------------------------------------
        # 4. PROCESAMIENTO DEL PDF (por ahora lo devolvemos igual)
        # ------------------------------------------------------------------
        processed_pdf_bytes = pdf_bytes

        # ------------------------------------------------------------------
        # 5. CODIFICAR DE NUEVO A BASE64 PARA POWER AUTOMATE
        # ------------------------------------------------------------------
        processed_b64 = base64.b64encode(processed_pdf_bytes).decode("utf-8")

        # ------------------------------------------------------------------
        # 6. RESPUESTA FINAL Compatible con SharePoint
        # ------------------------------------------------------------------
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
