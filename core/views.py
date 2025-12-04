import base64
import io
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

import pypdfium2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image


# ----------------------------------------------------------
# API DE SALUD
# ----------------------------------------------------------
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ----------------------------------------------------------
# API PARA CONVERTIR PDF A IMÁGENES Y DEVOLVER UN PDF FINAL
# ----------------------------------------------------------
@csrf_exempt
def convertir_pdf_imagenes(request):

    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # Obtener contenido enviado por Power Automate
        pdf_bytes = request.body

        if not pdf_bytes:
            return JsonResponse({"error": "No se recibió archivo PDF"}, status=400)

        # ----------------------------------------------------------
        # 1) Convertir PDF a imágenes usando pypdfium2
        # ----------------------------------------------------------
        pdf = pypdfium2.PdfDocument(pdf_bytes)
        num_pages = len(pdf)

        imagenes = []

        for i in range(num_pages):
            page = pdf[i]
            bitmap = page.render(scale=2)  # calidad alta
            pil_image = bitmap.to_pil()
            imagenes.append(pil_image)

        # ----------------------------------------------------------
        # 2) Crear PDF unificado con reportlab
        # ----------------------------------------------------------
        final_buffer = io.BytesIO()
        c = canvas.Canvas(final_buffer, pagesize=letter)

        for img in imagenes:
            # Convertir PIL a memoria temporal
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="JPEG")
            img_buffer.seek(0)

            # Ajustar tamaño dentro de la hoja
            page_width, page_height = letter
            c.drawImage(img_buffer, 0, 0, width=page_width, height=page_height)
            c.showPage()

        c.save()
        final_buffer.seek(0)

        # ----------------------------------------------------------
        # 3) Devolver PDF final como binario
        # ----------------------------------------------------------
        return HttpResponse(
            final_buffer.read(),
            content_type="application/pdf",
            status=200
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
