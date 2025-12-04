import base64
import json
import io
from urllib.parse import parse_qs

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes


@csrf_exempt
def convertir_pdf_imagenes(request):
    """
    Acepta datos desde Power Automate en dos formatos:

    1) JSON:
       {
         "$content": "<PDF_EN_BASE64>"
       }

    2) Form-url-encoded (tipo key=value&key2=value2):
       $content=<PDF_EN_BASE64>&$content-type=application/pdf
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # --------------------------------------------------
        # 1) LEER EL CUERPO COMO TEXTO
        # --------------------------------------------------
        raw_text = request.body.decode("utf-8", errors="ignore")

        data = None

        # --------------------------------------------------
        # 2) PRIMER INTENTO: PARSEAR COMO JSON
        # --------------------------------------------------
        try:
            data = json.loads(raw_text)
        except Exception:
            data = None

        # --------------------------------------------------
        # 3) SEGUNDO INTENTO: PARSEAR COMO QUERYSTRING
        #    (form-url-encoded: $content=...&$content-type=...)
        # --------------------------------------------------
        if not isinstance(data, dict):
            qs = parse_qs(raw_text)  # dict: clave -> [lista de valores]
            if qs:
                data = {k: v[0] for k, v in qs.items()}  # nos quedamos con el primer valor

        # Si todavía no tenemos un diccionario válido:
        if not isinstance(data, dict):
            return JsonResponse(
                {
                    "error": "No se pudo interpretar el cuerpo recibido.",
                    "detalle": "Formato no reconocido. Se intentó JSON y form-url-encoded.",
                    "raw_preview": raw_text[:200],
                },
                status=400,
            )

        # --------------------------------------------------
        # 4) EXTRAER $content
        # --------------------------------------------------
        content_b64 = data.get("$content") or data.get("content")

        if not content_b64:
            return JsonResponse(
                {
                    "error": "No se encontró '$content' en los datos recibidos.",
                    "datos_recibidos_keys": list(data.keys()),
                },
                status=400,
            )

        # --------------------------------------------------
        # 5) DECODIFICAR PDF
        # --------------------------------------------------
        try:
            pdf_bytes = base64.b64decode(content_b64)
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

        # --------------------------------------------------
        # 6) CONVERTIR PDF → IMÁGENES
        # --------------------------------------------------
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

        # --------------------------------------------------
        # 7) RESPUESTA PARA POWER AUTOMATE
        # --------------------------------------------------
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


