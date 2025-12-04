import base64
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health(request):
    """
    Endpoint simple de salud para verificar que el servicio está activo.
    URL: /api/health/
    """
    return JsonResponse(
        {"status": "ok", "message": "Proteccion_PDF activo"},
        status=200,
    )


@csrf_exempt
def proteger_pdf(request):
    """
    Endpoint que recibe un PDF desde Power Automate, en el formato:

        {
          "$content-type": "application/pdf",
          "$content": "BASE64_DEL_PDF"
        }

    y devuelve el MISMO PDF (por ahora sin modificaciones) en el mismo formato:

        {
          "$content-type": "application/pdf",
          "$content": "BASE64_DEL_PDF_PROCESADO"
        }

    Esto es exactamente lo que espera la acción "Crear archivo" de Power Automate.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "Solo se permite POST"},
            status=405,
        )

    try:
        # ------------------------------------------------------------------ #
        # 1) Leer el cuerpo tal cual lo envía Power Automate
        # ------------------------------------------------------------------ #
        raw_body = request.body

        if not raw_body:
            return JsonResponse(
                {"error": "El cuerpo de la petición está vacío."},
                status=400,
            )

        # Siempre vendrá como JSON, aunque el Content-Type sea octet-stream
        try:
            body_json = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "error": (
                        "Formato de cuerpo no válido. "
                        "Se esperaba JSON con campos '$content' y '$content-type' "
                        "tal como lo envía Power Automate."
                    )
                },
                status=400,
            )

        # ------------------------------------------------------------------ #
        # 2) Extraer el base64 del PDF
        # ------------------------------------------------------------------ #
        content_b64 = (
            body_json.get("$content")
            or body_json.get("content")
            or body_json.get("fileContent")
        )
        content_type = body_json.get("$content-type") or body_json.get(
            "contentType", ""
        )

        if not content_b64:
            return JsonResponse(
                {"error": "No se recibió ningún archivo 'pdf'"},
                status=400,
            )

        # Validación opcional de tipo
        if "pdf" not in content_type.lower():
            # Si quieres ser más permisivo, puedes quitar esta validación
            return JsonResponse(
                {"error": "El contenido recibido no es un PDF (content-type inválido)."},
                status=400,
            )

        # ------------------------------------------------------------------ #
        # 3) Decodificar el base64 a bytes
        # ------------------------------------------------------------------ #
        try:
            pdf_bytes = base64.b64decode(content_b64)
        except Exception as exc:
            return JsonResponse(
                {
                    "error": (
                        "No se pudo decodificar el contenido base64 recibido. "
                        f"Detalle: {str(exc)}"
                    )
                },
                status=400,
            )

        # Validar de forma muy simple que parezca un PDF
        if not pdf_bytes.startswith(b"%PDF"):
            # No devolvemos 500, sino un 400 controlado
            return JsonResponse(
                {
                    "error": (
                        "El contenido decodificado no parece ser un PDF "
                        "(no inicia con la cabecera %PDF)."
                    )
                },
                status=400,
            )

        # ------------------------------------------------------------------ #
        # 4) PROCESAMIENTO / PROTECCIÓN DEL PDF
        # ------------------------------------------------------------------ #
        # En este punto ya tienes los bytes reales del PDF en `pdf_bytes`.
        # Por ahora (para garantizar estabilidad) simplemente lo devolvemos
        # sin modificaciones. Más adelante aquí puedes:
        #   - aplicar contraseña
        #   - convertir páginas a imágenes
        #   - aplanar formularios, etc.
        #
        # Si más adelante quieres que aquí sí se “proteja” el PDF, lo hacemos,
        # pero por ahora dejamos la lógica mínima estable.
        processed_pdf_bytes = pdf_bytes

        # ------------------------------------------------------------------ #
        # 5) Volver a codificar a base64 para Power Automate
        # ------------------------------------------------------------------ #
        processed_b64 = base64.b64encode(processed_pdf_bytes).decode("utf-8")

        response_data = {
            "$content-type": "application/pdf",
            "$content": processed_b64,
        }

        return JsonResponse(response_data, status=200)

    except Exception as exc:  # Seguridad: captura de errores no previstos
        return JsonResponse(
            {"error": f"Error interno en el servidor: {str(exc)}"},
            status=500,
        )
